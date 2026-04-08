#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息格式化模块
负责日志消息的格式化和美化
"""
import json
import re
import logging
from typing import List, Dict
from models.log_record import LogRecord
from config.mappings import EventMappings
from utils.time_utils import TimeUtils

logger = logging.getLogger(__name__)


class MessageSplitter:
    """消息分段工具类"""
    
    # 各渠道消息长度限制
    CHANNEL_LIMITS = {
        'wecom': 2048,      # 企业微信 text 类型
        'dingtalk': 4000,   # 钉钉 text 类型
        'feishu': 4096,     # 飞书 text 类型
        'bark': 2000,       # Bark body 字段
        'pushplus': 5000,   # PushPlus
        'meow': 2000,       # MeoW msg 字段
        'webhook': 4000,    # Webhook 默认
        'default': 2000     # 默认限制
    }
    
    # 日志边界分隔符
    LOG_SEPARATOR = "─" * 6
    
    @classmethod
    def get_limit(cls, channel: str = 'default') -> int:
        """获取指定渠道的消息长度限制"""
        return cls.CHANNEL_LIMITS.get(channel.lower(), cls.CHANNEL_LIMITS['default'])
    
    @classmethod
    def _split_by_lines(cls, content: str, limit: int) -> List[str]:
        """
        按行分段，优先在换行处分割
        
        Args:
            content: 原始消息内容
            limit: 每段最大字符数
            
        Returns:
            分段后的消息列表
        """
        lines = content.split('\n')
        segments = []
        current = ""
        
        for line in lines:
            test_line = (current + '\n' + line).strip()
            
            if len(test_line) <= limit:
                current = test_line
            else:
                if current:
                    segments.append(current)
                if len(line) > limit:
                    chars = []
                    length = 0
                    for char in line:
                        char_len = 3 if ord(char) > 255 else 1
                        if length + char_len <= limit - 10:
                            chars.append(char)
                            length += char_len
                        else:
                            chars.append("...")
                            break
                    current = "".join(chars)
                else:
                    current = line
        
        if current:
            segments.append(current)
        
        return segments
    
    @classmethod
    def split_message(cls, content: str, limit: int) -> List[str]:
        """
        将消息分段
        
        Args:
            content: 原始消息内容
            limit: 每段最大字符数
            
        Returns:
            分段后的消息列表
        """
        if not content:
            return []
        
        if len(content) <= limit:
            return [content]
        
        return cls._split_by_lines(content, limit)
    
    @classmethod
    def split_for_channel(cls, content: str, channel: str) -> List[str]:
        """
        根据渠道限制分段消息
        
        Args:
            content: 原始消息内容
            channel: 渠道名称
            
        Returns:
            分段后的消息列表
        """
        limit = cls.get_limit(channel)
        return cls.split_message(content, limit)
    
    @classmethod
    def split_by_log_boundary(cls, content: str, channel: str) -> List[str]:
        """
        按日志边界分段，保持每条日志的完整性
        
        当消息包含多条日志时，按日志边界分割，确保：
        1. 每条日志内容保持完整
        2. 单条日志超长时再进行内部截断
        
        Args:
            content: 原始消息内容（可能包含多条日志）
            channel: 渠道名称
            
        Returns:
            分段后的消息列表
        """
        limit = cls.get_limit(channel)
        
        if not content:
            return []
        
        # 检查是否包含多条日志（通过分隔符判断）
        if cls.LOG_SEPARATOR not in content:
            # 单条日志，直接检查长度
            if len(content) <= limit:
                return [content]
            return cls.split_message(content, limit)
        
        # 按日志分隔符分割
        parts = content.split(cls.LOG_SEPARATOR)
        
        result = []
        current_segment = ""
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 如果单条日志就超长
            if len(part) > limit:
                # 先检查当前段是否有内容
                if current_segment:
                    result.append(current_segment)
                    current_segment = ""
                
                # 对超长日志进行内部截断
                chunks = cls.split_message(part, limit)
                result.extend(chunks)
            else:
                # 检查加上这一条是否会超限
                separator = "\n\n" if current_segment else ""
                test_content = current_segment + separator + part
                
                if len(test_content) <= limit:
                    current_segment = test_content
                else:
                    # 保存当前段，开启新段
                    if current_segment:
                        result.append(current_segment)
                    current_segment = part
        
        # 添加最后一段
        if current_segment:
            result.append(current_segment)
        
        # 添加序号前缀
        if len(result) > 1:
            final_result = []
            for i, seg in enumerate(result):
                # 清理可能存在的旧序号
                clean = re.sub(r'^\[\d+\]\s*', '', seg)
                clean = re.sub(r'^\[\d+/\d+\]\s*', '', clean)
                final_result.append(f"[{i+1}/{len(result)}] {clean}")
            return final_result
        
        return result


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
        message_parts.append(f"\n{MessageSplitter.LOG_SEPARATOR}")
        if log.parameter:
            message_parts.extend(self._format_parameter(log.parameter))
        
        message_parts.append(f"\n{MessageSplitter.LOG_SEPARATOR}")
        
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
            格式化后的消息字符串，使用统一分隔符连接多条日志
        """
        if not logs:
            return ""
        
        # 格式化每条日志
        messages = [self.format_single_log(log) for log in logs]
        
        # 使用统一分隔符连接多条日志，便于分段时保持边界
        return MessageSplitter.LOG_SEPARATOR.join(messages)
    
    def format_logs_for_display(self, logs: List[LogRecord], title: str = "日志列表") -> Dict[str, str]:
        """
        格式化日志列表用于显示（返回多个片段）
        
        Args:
            logs: 日志记录列表
            title: 显示标题
            
        Returns:
            包含 'content' 和 'count' 的字典
        """
        if not logs:
            return {"content": "暂无日志", "count": 0}
        
        content = self.format_batch_logs(logs)
        return {
            "content": content,
            "count": len(logs),
            "title": f"{title} ({len(logs)}条)"
        }
