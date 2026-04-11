#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送协调器模块

职责：
  - 接收待推送的 LogRecord 列表
  - 执行 DND（免打扰）判断
  - 调用推送服务发送消息
  - 记录推送历史

将 monitor_core/base.py 中的推送逻辑解耦至此，LogMonitor 只负责轮询和调度。
"""
import logging
from typing import List, Dict, Optional

from models.log_record import LogRecord
from models.push_history import PushHistory
from utils.message_formatter import MessageFormatter
from utils.time_utils import TimeUtils
from config.mappings import EventMappings

logger = logging.getLogger(__name__)


class PushCoordinator:
    """
    推送协调器

    封装 DND 判断 → 消息格式化 → 推送 → 历史记录 整个流程，
    供 LogMonitor 复用，避免在多处重复实现推送逻辑。
    """

    def __init__(self, push_service, history_service, dnd_service,
                 config: Dict, formatter: MessageFormatter = None,
                 time_utils: TimeUtils = None, mappings: EventMappings = None):
        """
        Args:
            push_service:    PushService 实例
            history_service: HistoryService 实例
            dnd_service:     DoNotDisturbService 实例
            config:          当前配置字典（引用，热更新友好）
            formatter:       MessageFormatter 实例（可选，默认新建）
            time_utils:      TimeUtils 实例（可选，默认新建）
            mappings:        EventMappings 实例（可选，默认新建）
        """
        self.push_service = push_service
        self.history_service = history_service
        self.dnd_service = dnd_service
        self.config = config
        self.formatter = formatter or MessageFormatter()
        self.time_utils = time_utils or TimeUtils()
        self.mappings = mappings or EventMappings()

    def push(self, logs: List[LogRecord], last_id: int,
             enabled_channels: Optional[Dict] = None) -> bool:
        """
        推送日志列表（含 DND 判断）。

        Args:
            logs:             待推送的日志列表
            last_id:          当前轮询的最大日志 ID（用于历史记录）
            enabled_channels: 推送渠道开关，None 时从 config 读取

        Returns:
            True 表示实际推送成功，False 表示被缓存或推送失败
        """
        if not logs:
            return False

        logger.debug(f"PushCoordinator.push: 收到 {len(logs)} 条日志")

        if enabled_channels is None:
            enabled_channels = self.config.get('push_channels', {})

        # DND 判断：在免打扰时段则缓存，不推送
        if self.dnd_service.should_cache_now():
            message = (
                self.formatter.format_single_log(logs[0])
                if len(logs) == 1
                else self.formatter.format_batch_logs(logs)
            )
            self.dnd_service.cache_message(message)
            logger.debug(f"[DND] 缓存 {len(logs)} 条消息")
            return False

        content = (
            self.formatter.format_single_log(logs[0])
            if len(logs) == 1
            else self.formatter.format_batch_logs(logs)
        )
        
        logger.debug(f"PushCoordinator.push: 调用 push_service.push_message")
        channel_results = self.push_service.push_message(content, enabled_channels)

        # 判断是否至少有一个渠道成功
        success = any(channel_results.values()) if channel_results else False
        
        # 记录实际推送的渠道结果
        self._record_history(logs, content, success, last_id, channel_results=channel_results if channel_results else None)

        logger.debug(f"PushCoordinator.push: 推送完成，{len(logs)} 条日志，success={success}")
        return success

    def push_raw(self, content: str, logs: List[LogRecord],
                 last_id: int, enabled_channels: Optional[Dict] = None,
                 count: Optional[int] = None) -> bool:
        """
        推送已格式化的消息（跳过内部格式化，供 DND 汇总等场景使用）。

        Args:
            content:          已格式化的消息内容
            logs:             对应的日志列表（用于统计）
            last_id:          当前最大日志 ID
            enabled_channels: 推送渠道开关
            count:            日志数量（可选，如果未提供则使用 len(logs)）
        """
        if enabled_channels is None:
            enabled_channels = self.config.get('push_channels', {})

        # DND 判断：在免打扰时段则缓存，不推送
        if self.dnd_service.should_cache_now():
            self.dnd_service.cache_message(content)
            logger.debug(f"push_raw: 消息已缓存（免打扰时段），content长度={len(content)}")
            return False

        channel_results = self.push_service.push_message(content, enabled_channels)
        success = any(channel_results.values()) if channel_results else False
        self._record_history(logs, content, success, last_id, count, channel_results=channel_results if channel_results else None)
        return success

    def build_preview(self, logs: List[LogRecord]) -> str:
        """构建推送历史预览字符串"""
        if not logs:
            return ""
        log = logs[0]
        preview = self.time_utils.timestamp_to_shanghai(log.logtime)
        if log.category is not None:
            category_name = self.mappings.get_category_name(log.category)
            preview += f" 🏷️分类: {category_name}"
        preview += " 单条日志" if len(logs) == 1 else f" {len(logs)}条日志"
        return preview

    def _record_history(self, logs: List[LogRecord], content: str,
                        success: bool, last_id: int, count: Optional[int] = None,
                        channel_results: Optional[Dict[str, bool]] = None):
        """
        写入推送历史

        Args:
            logs: 日志列表
            content: 消息内容
            success: 推送是否成功
            last_id: 最后日志ID
            count: 日志数量（可选，如果未提供则使用 len(logs)）
            channel_results: 渠道推送结果 {"wecom": True, "dingtalk": False}
        """
        # 如果未提供 count，则使用 logs 的长度
        log_count = count if count is not None else len(logs)

        level_counts: Dict[str, int] = {}
        for log in logs:
            level_name = self.mappings.get_level_name(log.loglevel)
            level_counts[level_name] = level_counts.get(level_name, 0) + 1

        history = PushHistory(
            timestamp=self.time_utils.get_current_datetime_str(),
            content=content,
            preview=self.build_preview(logs) if logs else f"汇总 {log_count} 条消息",
            success=success,
            count=log_count,
            last_id=last_id,
            levels=level_counts if logs else None,
            channel_results=channel_results
        )
        self.history_service.add_history(history)
