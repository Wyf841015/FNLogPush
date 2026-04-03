#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警聚合与降噪模块
AlertAggregator

功能：
  1. 聚合窗口：同一 (eventId, serviceId, loglevel) 组合在 window_seconds 内
     只推送一次；推送内容附带聚合计数，如「[聚合 8 次]」。
  2. 频率降噪：同一组合在 window_seconds 内超过 threshold 次触发
     「高频告警」模式，自动延长静默时间到 silence_seconds，
     避免消息轰炸。
  3. 每条聚合组在 window_seconds 到期后自动清空，重新计数。
  4. 线程安全（内部使用 threading.Lock）。
"""
import time
import threading
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from models.log_record import LogRecord

logger = logging.getLogger(__name__)


@dataclass
class AggregateGroup:
    """单个聚合组的状态"""
    key: tuple                          # (eventId, serviceId, loglevel)
    logs: List[LogRecord] = field(default_factory=list)  # 窗口内累积的日志
    window_start: float = field(default_factory=time.time)  # 窗口开始时间
    last_pushed_at: float = 0.0         # 上次推送时间（0 表示从未推送）
    push_count: int = 0                 # 本窗口内已推送次数
    total_count: int = 0                # 本窗口内累积条数（含未推送）
    silenced_until: float = 0.0         # 静默截止时间（高频降噪）

    @property
    def is_silenced(self) -> bool:
        return time.time() < self.silenced_until

    @property
    def window_age(self) -> float:
        return time.time() - self.window_start


class AlertAggregator:
    """
    告警聚合与降噪器

    用法示例：
        aggregator = AlertAggregator(window_seconds=300, threshold=5, silence_seconds=600)
        result = aggregator.feed(log_record)
        if result is not None:
            push(result.logs, result.count, result.is_aggregated)
    """

    def __init__(
        self,
        window_seconds: int = 300,
        threshold: int = 5,
        silence_seconds: int = 600,
        enabled: bool = True,
    ):
        """
        Args:
            window_seconds:  聚合窗口长度（秒），窗口内相同组合只推送一次
            threshold:       触发高频模式的计数阈值（窗口内超过此值进入静默）
            silence_seconds: 高频静默时长（秒）
            enabled:         是否启用聚合（False 时直通，不做任何聚合）
        """
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.silence_seconds = silence_seconds
        self.enabled = enabled

        self._groups: Dict[tuple, AggregateGroup] = {}
        self._lock = threading.Lock()

        # 统计
        self._stats = {
            "total_received": 0,
            "total_pushed": 0,
            "total_suppressed": 0,   # 被聚合/静默而未立即推送的条数
            "total_silenced": 0,     # 进入高频静默的组次数
        }

        logger.info(
            f"AlertAggregator 初始化: window={window_seconds}s, "
            f"threshold={threshold}, silence={silence_seconds}s, enabled={enabled}"
        )

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def update_config(
        self,
        window_seconds: Optional[int] = None,
        threshold: Optional[int] = None,
        silence_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
    ):
        """热更新聚合参数（不重置已有聚合组）"""
        with self._lock:
            if window_seconds is not None:
                self.window_seconds = window_seconds
            if threshold is not None:
                self.threshold = threshold
            if silence_seconds is not None:
                self.silence_seconds = silence_seconds
            if enabled is not None:
                self.enabled = enabled
        logger.info(
            f"AlertAggregator 参数更新: window={self.window_seconds}s, "
            f"threshold={self.threshold}, silence={self.silence_seconds}s, "
            f"enabled={self.enabled}"
        )

    @dataclass
    class FeedResult:
        """feed() 的返回值：需要实际推送时返回此对象，否则返回 None"""
        logs: List[LogRecord]     # 本次应推送的日志列表（首条 + 聚合代表）
        count: int                # 窗口内累积总条数（含本次）
        is_aggregated: bool       # True 表示是聚合推送（count > 1）
        suppressed: int           # 本次未立即推送而被压制的额外条数
        key: tuple                # 对应的聚合键

    def feed(self, log: LogRecord) -> Optional["AlertAggregator.FeedResult"]:
        """
        投入一条日志，返回是否需要推送。

        Returns:
            FeedResult  — 需要推送
            None        — 该条日志被聚合/静默，暂不推送
        """
        if not self.enabled:
            # 聚合关闭时直通
            with self._lock:
                self._stats["total_received"] += 1
                self._stats["total_pushed"] += 1
            return self.FeedResult(
                logs=[log], count=1, is_aggregated=False,
                suppressed=0, key=self._make_key(log)
            )

        key = self._make_key(log)
        now = time.time()

        with self._lock:
            self._stats["total_received"] += 1
            group = self._groups.get(key)

            # ── 1. 窗口已过期：清空并重新开始 ──────────────────────────
            if group is not None and group.window_age > self.window_seconds:
                logger.debug(f"[聚合] 窗口到期，重置: {key}")
                del self._groups[key]
                group = None

            # ── 2. 首条：创建聚合组并立即推送 ──────────────────────────
            if group is None:
                group = AggregateGroup(key=key, window_start=now)
                group.logs.append(log)
                group.total_count = 1
                group.push_count = 1
                group.last_pushed_at = now
                self._groups[key] = group
                self._stats["total_pushed"] += 1
                return self.FeedResult(
                    logs=[log], count=1, is_aggregated=False,
                    suppressed=0, key=key
                )

            # ── 3. 窗口内后续条：累积但不立即推送 ─────────────────────
            group.logs.append(log)
            group.total_count += 1

            # 3a. 高频静默检测
            if group.total_count > self.threshold and not group.is_silenced:
                group.silenced_until = now + self.silence_seconds
                self._stats["total_silenced"] += 1
                logger.warning(
                    f"[聚合] 高频告警，进入静默 {self.silence_seconds}s: "
                    f"key={key}, count={group.total_count}"
                )

            if group.is_silenced:
                self._stats["total_suppressed"] += 1
                logger.debug(
                    f"[聚合] 静默中，跳过推送: key={key}, count={group.total_count}"
                )
                return None

            # 3b. 正常聚合：窗口内只有首次立即推送，后续压制
            self._stats["total_suppressed"] += 1
            logger.debug(
                f"[聚合] 窗口内压制: key={key}, count={group.total_count}"
            )
            return None

    def flush_expired(self) -> List["AlertAggregator.FeedResult"]:
        """
        清理所有已到期窗口，并对其中「有积压但尚未推送聚合摘要」的组
        生成一条聚合摘要推送结果返回。

        供监控主循环定期调用（建议每 window_seconds/2 调用一次）。
        """
        now = time.time()
        results = []
        with self._lock:
            expired_keys = [
                k for k, g in self._groups.items()
                if g.window_age > self.window_seconds
            ]
            for key in expired_keys:
                group = self._groups.pop(key)
                # 如果窗口内累积了超过 1 条，且推送次数只有 1（首条），
                # 则补发一条聚合摘要
                suppressed = group.total_count - group.push_count
                if suppressed > 0:
                    self._stats["total_pushed"] += 1
                    results.append(self.FeedResult(
                        logs=group.logs,
                        count=group.total_count,
                        is_aggregated=True,
                        suppressed=suppressed,
                        key=key,
                    ))
                    logger.info(
                        f"[聚合] 窗口到期，补发聚合摘要: key={key}, "
                        f"total={group.total_count}, suppressed={suppressed}"
                    )
        return results

    def get_stats(self) -> Dict:
        """返回统计信息（线程安全快照）"""
        with self._lock:
            active = len(self._groups)
            silenced = sum(1 for g in self._groups.values() if g.is_silenced)
            return {
                **self._stats,
                "active_groups": active,
                "silenced_groups": silenced,
                "window_seconds": self.window_seconds,
                "threshold": self.threshold,
                "silence_seconds": self.silence_seconds,
                "enabled": self.enabled,
            }

    def get_active_groups(self) -> List[Dict]:
        """返回当前所有活跃聚合组的快照（供 API 查询）"""
        now = time.time()
        with self._lock:
            result = []
            for key, group in self._groups.items():
                result.append({
                    "event_id": key[0],
                    "service_id": key[1],
                    "loglevel": key[2],
                    "total_count": group.total_count,
                    "push_count": group.push_count,
                    "suppressed": group.total_count - group.push_count,
                    "window_age_s": round(group.window_age, 1),
                    "window_remaining_s": max(0.0, round(self.window_seconds - group.window_age, 1)),
                    "is_silenced": group.is_silenced,
                    "silenced_remaining_s": max(0.0, round(group.silenced_until - now, 1)) if group.is_silenced else 0,
                })
        return result

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(log: LogRecord) -> tuple:
        """聚合键：(eventId, serviceId, loglevel)"""
        return (
            log.eventId or '',
            log.serviceId or '',
            log.loglevel if log.loglevel is not None else -1,
        )
