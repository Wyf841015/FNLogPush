#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息格式化模块
负责日志消息的格式化和美化
"""
import json
import logging
from typing import List, Dict
from models.log_record import LogRecord
from config.mappings import EventMappings
from utils.time_utils import TimeUtils

logger = logging.getLogger(__name__)


class MessageFormatter:
    """消息格式化类"""
    
    def __init__(self):
        self.mappings = EventMappings()
        self.time_utils = TimeUtils()
    
    def format_single_log(self, log: LogRecord) -> str:
        """
        格式化单条日志记录
        
        Args:
            log: 日志记录对象
            
        Returns:
            格式化后的消息字符串
        """
        message_parts = []
        
        # 获取日志级别
        log_level = self.mappings.get_level_name(log.loglevel)
        icon = self.mappings.get_level_icon(log_level)
        
        # 添加分类
        if log.category is not None:
            log_category = self.mappings.get_category_name(log.category)
            message_parts.append(f"🏷️分类: {log_category}")
        
        # 添加时间
        log_time = self.time_utils.timestamp_to_shanghai(log.logtime)
        message_parts.append(f"🕐时间: {log_time}")
        
        # 添加级别
        message_parts.append(f"📝级别: {log_level}")
        
        # 添加事件
        if log.eventId:
            event_name = self.mappings.get_event_name(log.eventId)
            message_parts.append(f"📋事件: {event_name} - {log.eventId}")
        
        # 添加服务
        if log.serviceId:
            message_parts.append(f"🌐服务: {log.serviceId}")
        
        # 添加用户
        if log.uname:
            message_parts.append(f"👤用户: {log.uname}")
        
        # 添加参数
        message_parts.append(f"\n --------------")
        if log.parameter:
            message_parts.extend(self._format_parameter(log.parameter))
        
        message_parts.append(f"\n --------------")
        
        return "\n".join(message_parts)
    
    def _format_parameter(self, parameter: str) -> List[str]:
        """
        格式化参数
        
        Args:
            parameter: 参数字符串
            
        Returns:
            格式化后的参数行列表
        """
        try:
            param_dict = json.loads(parameter)
            lines = [" 附加信息:"]
            
            for key, value in param_dict.items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                    value_lines = value_str.split('\n')
                    for j, line in enumerate(value_lines):
                        if j == 0:
                            lines.append(f"     {key}: {line}")
                        else:
                            lines.append(f"          {line}")
                else:
                    lines.append(f"     {key}: {value}")
            
            return lines
        except json.JSONDecodeError:
            return [f"   参数: {parameter}"]
        except Exception as e:
            logger.warning(f"解析参数时出错: {e}")
            return [f"   参数: {parameter} (解析失败)"]
    
    def format_batch_logs(self, logs: List[LogRecord]) -> str:
        """
        格式化批量日志记录
        
        Args:
            logs: 日志记录列表
            
        Returns:
            格式化后的消息字符串
        """
        if not logs:
            return ""
        
        # 格式化每条日志
        messages = [self.format_single_log(log) for log in logs]
        
        # 构建批量消息头
        separator = "─" * 6
        current_time = self.time_utils.get_current_datetime_str()
        
        # 统计各级别数量
        level_counts = {}
        for log in logs:
            log_level = self.mappings.get_level_name(log.loglevel)
            level_counts[log_level] = level_counts.get(log_level, 0) + 1
        
        # 构建完整消息
        if len(logs) == 1:
            content = f"📢 新日志哨兵\n{messages[0]}"
        else:
            stats_text = "，".join([f"{count}{level}" for level, count in level_counts.items()])
            content = f"📢 批量日志哨兵 ({len(logs)}条)\n"
            content += f"📊 分布: {stats_text}\n"
            content += f"{separator}\n"
            content += "\n\n".join(messages)
        
        return content
    
    def format_dnd_summary(self, cached_messages: List[str]) -> str:
        """
        格式化免打扰时段消息汇总
        
        Args:
            cached_messages: 缓存的消息列表
            
        Returns:
            格式化后的汇总消息
        """
        if len(cached_messages) == 1:
            return f"【免打扰时段消息汇总】\n{cached_messages[0]}"
        else:
            content = f"【免打扰时段消息汇总】共 {len(cached_messages)} 条消息\n\n"
            for i, msg in enumerate(cached_messages, 1):
                content += f"第{i}条消息\n {msg}\n"
            return content
