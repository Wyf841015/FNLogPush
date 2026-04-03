#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置 Schema 定义和验证模块
使用 JSON Schema 风格进行配置验证
"""
import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Callable

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Schema 验证器"""
    
    # Schema 定义
    SCHEMA: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "database_path": {"type": "string", "minLength": 1},
            "webhook_url": {"type": "string"},
            "check_interval": {"type": "number", "minimum": 1, "maximum": 3600},
            "log_levels": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            },
            "selected_levels": {
                "type": "array",
                "items": {"type": "string"}
            },
            "event_ids": {"type": "array", "items": {"type": "integer"}},
            "selected_events": {"type": "array", "items": {"type": "string"}},
            "web_host": {"type": "string", "pattern": r"^[\d\.]+$|^localhost$|^[\w\.-]+$"},
            "web_port": {"type": "integer", "minimum": 1, "maximum": 65535},
            "history_size": {"type": "integer", "minimum": 10, "maximum": 100000},
            "do_not_disturb": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "start_time": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
                    "end_time": {"type": "string", "pattern": r"^\d{2}:\d{2}$"}
                },
                "required": ["enabled", "start_time", "end_time"]
            },
            "wecom": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "webhook_url": {"type": "string"},
                    "corp_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "secret": {"type": "string"},
                    "touser": {"type": "string"}
                },
                "required": ["enabled"]
            },
            "dingtalk": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "webhook_url": {"type": "string"},
                    "secret": {"type": "string"}
                },
                "required": ["enabled"]
            },
            "feishu": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "webhook_url": {"type": "string"}
                },
                "required": ["enabled"]
            },
            "bark": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "server_url": {"type": "string"}
                },
                "required": ["enabled"]
            },
            "pushplus": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "token": {"type": "string"}
                },
                "required": ["enabled"]
            },
            "push_channels": {
                "type": "object",
                "properties": {
                    "webhook": {"type": "boolean"},
                    "wecom": {"type": "boolean"},
                    "dingtalk": {"type": "boolean"},
                    "feishu": {"type": "boolean"},
                    "bark": {"type": "boolean"},
                    "pushplus": {"type": "boolean"}
                }
            },
            "backup_monitor": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "database_path": {"type": "string"},
                    "status_filter": {
                        "type": "array",
                        "items": {"type": "integer"}
                    },
                    "check_interval": {"type": "number", "minimum": 1}
                }
            },
            "alert_aggregation": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "window_seconds": {"type": "integer", "minimum": 1},
                    "threshold": {"type": "integer", "minimum": 1},
                    "silence_seconds": {"type": "integer", "minimum": 0}
                },
                "required": ["enabled", "window_seconds", "threshold", "silence_seconds"]
            }
        },
        "required": ["database_path", "check_interval", "web_port"]
    }
    
    def __init__(self):
        """初始化验证器"""
        self.errors: List[str] = []
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证配置是否符合 Schema
        
        Args:
            config: 配置字典
            
        Returns:
            (是否有效, 错误信息列表)
        """
        self.errors = []
        
        # 验证顶层类型
        if not isinstance(config, dict):
            return (False, ["配置必须是字典类型"])
        
        # 验证必需字段
        required_fields = self.SCHEMA.get("required", [])
        for field in required_fields:
            if field not in config:
                self.errors.append(f"缺少必需字段: {field}")
        
        # 验证每个字段
        properties = self.SCHEMA.get("properties", {})
        self._validate_object(config, properties, "")
        
        return (len(self.errors) == 0, self.errors)
    
    def _validate_object(self, obj: Dict[str, Any], schema_props: Dict[str, Any], path: str):
        """递归验证对象"""
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            
            if key not in schema_props:
                continue  # 忽略未知字段
            
            schema = schema_props[key]
            schema_type = schema.get("type")
            
            # 类型验证
            if schema_type == "string":
                if not isinstance(value, str):
                    self.errors.append(f"{current_path}: 期望字符串，实际为 {type(value).__name__}")
                elif "minLength" in schema and len(value) < schema["minLength"]:
                    self.errors.append(f"{current_path}: 长度不能小于 {schema['minLength']}")
                elif "pattern" in schema and not re.match(schema["pattern"], value):
                    self.errors.append(f"{current_path}: 格式不符合要求 ({schema['pattern']})")
            
            elif schema_type == "number":
                if not isinstance(value, (int, float)):
                    self.errors.append(f"{current_path}: 期望数字，实际为 {type(value).__name__}")
                elif "minimum" in schema and value < schema["minimum"]:
                    self.errors.append(f"{current_path}: 不能小于 {schema['minimum']}")
                elif "maximum" in schema and value > schema["maximum"]:
                    self.errors.append(f"{current_path}: 不能大于 {schema['maximum']}")
            
            elif schema_type == "integer":
                if not isinstance(value, int) or isinstance(value, bool):
                    self.errors.append(f"{current_path}: 期望整数，实际为 {type(value).__name__}")
                elif "minimum" in schema and value < schema["minimum"]:
                    self.errors.append(f"{current_path}: 不能小于 {schema['minimum']}")
                elif "maximum" in schema and value > schema["maximum"]:
                    self.errors.append(f"{current_path}: 不能大于 {schema['maximum']}")
            
            elif schema_type == "boolean":
                if not isinstance(value, bool):
                    self.errors.append(f"{current_path}: 期望布尔值，实际为 {type(value).__name__}")
            
            elif schema_type == "array":
                if not isinstance(value, list):
                    self.errors.append(f"{current_path}: 期望数组，实际为 {type(value).__name__}")
                elif "minItems" in schema and len(value) < schema["minItems"]:
                    self.errors.append(f"{current_path}: 数组长度不能小于 {schema['minItems']}")
                elif "items" in schema and "type" in schema["items"]:
                    item_type = schema["items"]["type"]
                    for i, item in enumerate(value):
                        item_path = f"{current_path}[{i}]"
                        if item_type == "string" and not isinstance(item, str):
                            self.errors.append(f"{item_path}: 期望字符串")
                        elif item_type == "integer" and (not isinstance(item, int) or isinstance(item, bool)):
                            self.errors.append(f"{item_path}: 期望整数")
            
            elif schema_type == "object":
                if not isinstance(value, dict):
                    self.errors.append(f"{current_path}: 期望对象，实际为 {type(value).__name__}")
                elif "properties" in schema:
                    self._validate_object(value, schema["properties"], current_path)
    
    def validate_webhook_url(self, url: str) -> Tuple[bool, str]:
        """
        验证 Webhook URL
        
        Args:
            url: Webhook URL
            
        Returns:
            (是否有效, 错误信息)
        """
        if not url:
            return (True, "")  # 空URL视为有效（可选配置）
        
        # 检查是否为有效URL格式
        url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return (False, "URL格式不正确")
        
        return (True, "")