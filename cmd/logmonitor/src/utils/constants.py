#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
常量定义模块
集中管理全项目使用的常量，避免 Magic Numbers
"""
from enum import IntEnum


# ============= 日志级别 =============
class LogLevel(IntEnum):
    """日志级别枚举"""
    DEBUG = 1      # 调试
    INFO = 2       # 普通
    WARNING = 4     # 警告
    ERROR = 8      # 错误
    CRITICAL = 16  # 严重错误


# 日志级别名称映射
LOG_LEVEL_NAMES = {
    1: '调试',
    2: '普通',
    4: '警告',
    8: '错误',
    16: '严重错误'
}

# 日志级别图标
LOG_LEVEL_ICONS = {
    '调试': '🔵',
    '普通': '⚪',
    '警告': '🟡',
    '错误': '🔴',
    '严重错误': '🚨'
}


# ============= 备份状态 =============
class BackupStatus(IntEnum):
    """备份状态枚举"""
    RUNNING = 1    # 运行中
    SUCCESS = 2    # 成功
    FAILED = 3     # 失败
    CANCELLED = 4  # 已取消


# 备份状态名称
BACKUP_STATUS_NAMES = {
    1: '运行中',
    2: '成功',
    3: '失败',
    4: '已取消'
}


# ============= 数据库状态 =============
class DBStatus:
    """数据库连接状态"""
    CONNECTED = 'connected'
    FAILED = 'failed'
    DISCONNECTED = 'disconnected'


# ============= 推送状态 =============
class PushStatus:
    """推送结果状态"""
    SUCCESS = 'success'
    FAILED = 'failed'
    PENDING = 'pending'


# ============= 时间常量（秒） =============
class TimeConstants:
    """时间常量"""
    # Session
    SESSION_TIMEOUT = 300              # 5分钟无操作超时
    SESSION_LIFETIME = 86400 * 7      # 7天持久化
    
    # 推送重试
    PUSH_RETRY_INTERVAL = 60           # 重试间隔 60秒
    MAX_CONSECUTIVE_ERRORS = 10       # 最大连续错误数
    
    # 告警聚合
    DEFAULT_WINDOW_SECONDS = 300      # 聚合窗口 5分钟
    DEFAULT_SILENCE_SECONDS = 600     # 静默时间 10分钟
    DEFAULT_THRESHOLD = 5             # 聚合阈值
    
    # 刷新间隔
    DEFAULT_CHECK_INTERVAL = 5         # 默认检查间隔 5秒
    DEFAULT_BACKUP_INTERVAL = 10      # 备份检查间隔 10秒
    HEALTH_PUSH_INTERVAL = 15         # 健康状态推送间隔 15秒


# ============= 默认配置 =============
class DefaultConfig:
    """默认配置值"""
    DATABASE_PATH = 'logger_data.db3'
    HISTORY_SIZE = 1000
    WEB_PORT = 5000
    WEB_HOST = '0.0.0.0'
    UI_PORT = 19800


# ============= 敏感字段列表 =============
SENSITIVE_FIELDS = [
    'webhook_url',
    'wecom.webhook_url',
    'wecom.secret',
    'dingtalk.webhook_url',
    'dingtalk.secret',
    'feishu.webhook_url',
    'bark.device_key',
    'pushplus.token',
    'meow.token',
]
