#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责配置文件的加载、更新和验证
"""
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

from .schema import SchemaValidator

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "database_path": "logger_data.db3",
        "webhook_url": "",
        "check_interval": 5,
        "log_levels": ["调试", "普通", "警告", "错误", "严重错误"],
        "selected_levels": ["普通", "警告", "错误", "严重错误"],
        "event_ids": [
            # 存储管理
            "CreateStorage", "MountStorage", "UnmountStorage", "DeleteStorage",
            "STORAGE_MOUNT_SUCCESS", "STORAGE_MOUNT_FAILED",
            "STORAGE_UMOUNT_SUCCESS", "STORAGE_UMOUNT_FAILED",
            # 防火墙
            "FW_ENABLE", "FW_DISABLE", "FW_START_SUCCESS", "FW_START_FAILED",
            "FW_STOP_SUCCESS", "FW_STOP_FAILED"
        ],
        "selected_events": [],
        "web_host": "0.0.0.0",
        "web_port": 5000,
        "history_size": 1000,
        "do_not_disturb": {
            "enabled": False,
            "start_time": "23:00",
            "end_time": "08:00"
        },
        "wecom": {
            "enabled": False,
            "webhook_url": "",
            "corp_id": "",
            "agent_id": "",
            "secret": "",
            "touser": "@all"
        },
        "push_channels": {
            "webhook": True,
            "wecom": False
        },
        "backup_monitor": {
            "enabled": False,
            "database_path": "",
            "status_filter": [1, 2, 3, 4],
            "check_interval": 10
        },
        "alert_aggregation": {
            "enabled": True,
            "window_seconds": 300,
            "threshold": 5,
            "silence_seconds": 600
        }
    }
    
    def __init__(self, config_path: str = 'config.json'):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.validator = SchemaValidator()
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                return self.DEFAULT_CONFIG.copy()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置，确保所有必需的键都存在
                merged_config = self.DEFAULT_CONFIG.copy()
                merged_config.update(config)
                
                # 合并 event_ids 列表：将新增的默认事件追加到用户已有列表中
                if 'event_ids' in config and isinstance(config['event_ids'], list):
                    default_ids = set(self.DEFAULT_CONFIG.get('event_ids', []))
                    user_ids = set(config['event_ids'])
                    # 保留用户已有的 + 添加默认值中用户没有的
                    merged_config['event_ids'] = list(user_ids | default_ids)
                
                # Schema 验证
                is_valid, errors = self.validator.validate(merged_config)
                if not is_valid:
                    logger.warning(f"配置验证失败: {errors}")
                
                return merged_config
                
        except json.JSONDecodeError as e:
            logger.error(f"配置文件JSON解析错误: {e}")
            return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"加载配置文件时出错: {e}")
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否保存成功
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            logger.info(f"配置已保存到: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件时出错: {e}")
            return False
    
    @staticmethod
    def _strip_masked(new: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归过滤掉脱敏占位符 '***'。
        当新配置里某个字段的值为 '***' 时，保留 current 里的真实值，
        防止前端把脱敏响应体直接 POST 回来导致真实密钥被覆盖。
        """
        result = {}
        for k, v in new.items():
            if isinstance(v, dict):
                result[k] = ConfigManager._strip_masked(v, current.get(k, {}) if isinstance(current.get(k), dict) else {})
            elif v == "***":
                # 保留当前内存里的真实值（若存在）
                if k in current and current[k] != "***":
                    result[k] = current[k]
                # 否则跳过，不写入
            else:
                result[k] = v
        return result

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            new_config: 新的配置项
            
        Returns:
            是否更新成功
        """
        try:
            logger.info(f"更新配置: {list(new_config.keys())}")
            safe_config = self._strip_masked(new_config, self.config)
            self.config.update(safe_config)
            return self.save_config()
        except Exception as e:
            logger.error(f"更新配置时出错: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def get_nested(self, *keys, default=None) -> Any:
        """
        获取嵌套配置项
        
        Args:
            *keys: 配置键路径
            default: 默认值
            
        Returns:
            配置值
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """
        验证配置有效性
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查数据库路径
        if not self.config.get('database_path'):
            errors.append("数据库路径未配置")
        
        # 检查检查间隔
        interval = self.config.get('check_interval', 5)
        if not isinstance(interval, (int, float)) or interval <= 0:
            errors.append("检查间隔必须为正数")
        
        # 检查Web端口
        port = self.config.get('web_port', 5000)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("Web端口必须在1-65535之间")
        
        # 检查推送渠道配置
        push_channels = self.config.get('push_channels', {})
        if not isinstance(push_channels, dict):
            errors.append("push_channels必须为字典类型")
        
        # 检查免打扰时间格式
        dnd = self.config.get('do_not_disturb', {})
        if dnd.get('enabled'):
            start = dnd.get('start_time', '')
            end = dnd.get('end_time', '')
            if not self._validate_time_format(start) or not self._validate_time_format(end):
                errors.append("免打扰时间格式不正确，应为HH:MM格式")
        
        return (len(errors) == 0, errors)
    
    def _validate_time_format(self, time_str: str) -> bool:
        """
        验证时间格式
        
        Args:
            time_str: 时间字符串
            
        Returns:
            是否有效
        """
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            hour = int(parts[0])
            minute = int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AttributeError, TypeError):
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证配置是否符合 Schema
        
        Args:
            config: 配置字典
            
        Returns:
            (是否有效, 错误信息列表)
        """
        return self.validator.validate(config)
    
    def validate_webhook_url(self, url: str) -> Tuple[bool, str]:
        """
        验证 Webhook URL
        
        Args:
            url: Webhook URL
            
        Returns:
            (是否有效, 错误信息)
        """
        return self.validator.validate_webhook_url(url)
    
    def get_schema(self) -> Dict[str, Any]:
        """
        获取配置 Schema
        
        Returns:
            Schema 定义
        """
        return self.validator.SCHEMA
