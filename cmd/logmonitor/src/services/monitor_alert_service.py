#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控告警服务模块
监控系统健康状态，在推送失败时自动告警
"""
import logging
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    PUSH_FAILURE = "push_failure"
    DATABASE_ERROR = "database_error"
    MONITOR_STOPPED = "monitor_stopped"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    DISK_FULL = "disk_full"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"


@dataclass
class Alert:
    """告警数据类"""
    alert_id: str
    level: AlertLevel
    type: AlertType
    title: str
    message: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[float] = None


class MonitorAlertService:
    """监控告警服务类"""

    def __init__(self, alert_callback: Optional[Callable] = None):
        """
        初始化告警服务

        Args:
            alert_callback: 告警回调函数
        """
        self._alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._lock = threading.RLock()
        self._alert_callback = alert_callback

        # 配置
        self._config = {
            'max_alerts': 100,
            'alert_retention_time': 3600 * 24,
            'push_failure_threshold': 3,
            'cpu_threshold': 80,
            'memory_threshold': 85,
            'disk_threshold': 90,
        }

        # 统计
        self._stats = {
            'total_alerts': 0,
            'push_failures': 0,
            'resolved_alerts': 0
        }

        # 告警冷却
        self._cooldowns: Dict[str, float] = {}
        self._cooldown_time = 300

    def configure(self, config: Dict):
        """配置告警服务"""
        self._config.update(config)

    def add_alert(self, level: AlertLevel, alert_type: AlertType,
                  title: str, message: str, metadata: Optional[Dict] = None) -> Optional[Alert]:
        """添加告警"""
        alert_key = f"{alert_type.value}_{level.value}"
        current_time = time.time()

        if alert_key in self._cooldowns:
            if current_time - self._cooldowns[alert_key] < self._cooldown_time:
                logger.debug(f"告警处于冷却期，跳过: {alert_key}")
                return None

        with self._lock:
            self._stats['total_alerts'] += 1
            alert_id = f"alert_{self._stats['total_alerts']}_{int(current_time * 1000)}"

            alert = Alert(
                alert_id=alert_id,
                level=level,
                type=alert_type,
                title=title,
                message=message,
                metadata=metadata or {}
            )

            self._alerts[alert_id] = alert
            self._alert_history.append(alert)
            self._cleanup_old_alerts()
            self._cooldowns[alert_key] = current_time

            if alert_type == AlertType.PUSH_FAILURE:
                self._stats['push_failures'] += 1

            if self._alert_callback:
                try:
                    self._alert_callback(alert)
                except Exception as e:
                    logger.error(f"告警回调执行失败: {e}")

            logger.warning(f"告警已创建: [{level.value}] {title} - {message}")
            return alert

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        with self._lock:
            if alert_id not in self._alerts:
                return False

            alert = self._alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = time.time()
            self._stats['resolved_alerts'] += 1
            logger.info(f"告警已解决: {alert_id}")
            return True

    def resolve_by_type(self, alert_type: AlertType) -> int:
        """按类型解决告警"""
        count = 0
        with self._lock:
            for alert_id, alert in self._alerts.items():
                if alert.type == alert_type and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = time.time()
                    count += 1
                    self._stats['resolved_alerts'] += 1

        if count > 0:
            logger.info(f"已解决 {count} 个 {alert_type.value} 类型的告警")
        return count

    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """获取活动告警"""
        with self._lock:
            alerts = [a for a in self._alerts.values() if not a.resolved]
            if level:
                alerts = [a for a in alerts if a.level == level]
            return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        """获取告警历史"""
        with self._lock:
            return sorted(self._alert_history, key=lambda x: x.timestamp, reverse=True)[:limit]

    def _cleanup_old_alerts(self):
        """清理过期的告警"""
        current_time = time.time()
        to_remove = []

        for alert_id, alert in self._alerts.items():
            if current_time - alert.timestamp > self._config['alert_retention_time']:
                to_remove.append(alert_id)

        for alert_id in to_remove:
            del self._alerts[alert_id]

        while len(self._alerts) > self._config['max_alerts']:
            oldest = min(self._alerts.values(), key=lambda x: x.timestamp)
            del self._alerts[oldest.alert_id]

        if to_remove:
            logger.debug(f"清理了 {len(to_remove)} 个过期告警")

    def check_push_failure(self, failure_count: int, channel: str) -> bool:
        """检查推送失败并创建告警"""
        threshold = self._config['push_failure_threshold']

        if failure_count >= threshold:
            self.add_alert(
                level=AlertLevel.ERROR,
                alert_type=AlertType.PUSH_FAILURE,
                title="推送失败告警",
                message=f"渠道 '{channel}' 连续 {failure_count} 次推送失败",
                metadata={'channel': channel, 'failure_count': failure_count}
            )
            return True
        return False

    def check_system_health(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """检查系统健康状态"""
        if cpu_percent >= self._config['cpu_threshold']:
            self.add_alert(
                level=AlertLevel.WARNING,
                alert_type=AlertType.HIGH_CPU,
                title="CPU使用率过高",
                message=f"CPU使用率: {cpu_percent:.1f}%",
                metadata={'cpu_percent': cpu_percent}
            )

        if memory_percent >= self._config['memory_threshold']:
            self.add_alert(
                level=AlertLevel.WARNING,
                alert_type=AlertType.HIGH_MEMORY,
                title="内存使用率过高",
                message=f"内存使用率: {memory_percent:.1f}%",
                metadata={'memory_percent': memory_percent}
            )

        if disk_percent >= self._config['disk_threshold']:
            self.add_alert(
                level=AlertLevel.CRITICAL,
                alert_type=AlertType.DISK_FULL,
                title="磁盘空间不足",
                message=f"磁盘使用率: {disk_percent:.1f}%",
                metadata={'disk_percent': disk_percent}
            )

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            return {
                **self._stats,
                'active_alerts': len([a for a in self._alerts.values() if not a.resolved]),
                'active_error_alerts': len([
                    a for a in self._alerts.values()
                    if not a.resolved and a.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]
                ])
            }


# 全局告警服务实例
_alert_service: Optional[MonitorAlertService] = None


def get_alert_service() -> MonitorAlertService:
    """获取全局告警服务实例"""
    global _alert_service
    if _alert_service is None:
        _alert_service = MonitorAlertService()
    return _alert_service
