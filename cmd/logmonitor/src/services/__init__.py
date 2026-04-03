#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services 包初始化文件

该包包含系统的核心服务模块，包括：
- 数据库服务：处理与SQLite数据库的交互
- 推送服务：处理各种推送渠道的消息发送
- 认证服务：处理用户认证和权限管理
- 历史记录服务：管理推送历史记录
- 免打扰服务：管理免打扰时间段设置
- 备份监控服务：监控备份操作
- 任务队列服务：异步任务处理
- 监控告警服务：系统健康监控和告警
"""

from .database_service import DatabaseService
from .push_service import PushService
from .auth_service import AuthService
from .history_service import HistoryService
from .dnd_service import DoNotDisturbService
from .backup_monitor_service import BackupMonitorService

# 尝试导入新服务（如果存在）
try:
    from .task_queue import TaskQueue, get_task_queue, submit_task, submit_async
except ImportError:
    TaskQueue = None
    get_task_queue = None
    submit_task = None
    submit_async = None

try:
    from .monitor_alert_service import (
        MonitorAlertService,
        AlertLevel,
        AlertType,
        Alert,
        get_alert_service
    )
except ImportError:
    MonitorAlertService = None
    AlertLevel = None
    AlertType = None
    Alert = None
    get_alert_service = None


__all__ = [
    'DatabaseService',
    'PushService',
    'AuthService',
    'HistoryService',
    'DoNotDisturbService',
    'BackupMonitorService',
    # Task Queue
    'TaskQueue',
    'get_task_queue',
    'submit_task',
    'submit_async',
    # Monitor Alert
    'MonitorAlertService',
    'AlertLevel',
    'AlertType',
    'Alert',
    'get_alert_service'
]
