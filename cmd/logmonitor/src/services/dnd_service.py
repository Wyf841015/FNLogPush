#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
免打扰服务模块
负责免打扰模式的管理和消息缓存
"""
import logging
from typing import List, Dict, Any, Optional
from utils.time_utils import TimeUtils

logger = logging.getLogger(__name__)


class DoNotDisturbService:
    """免打扰服务类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化免打扰服务
        
        Args:
            config: 免打扰配置字典
        """
        self.config = config
        self.cached_messages: List[str] = []
        self.time_utils = TimeUtils()
    
    def update_config(self, config: Dict[str, Any]):
        """
        更新配置
        
        Args:
            config: 新的配置字典
        """
        self.config = config
        logger.debug("免打扰服务配置已更新")
    
    def is_enabled(self) -> bool:
        """
        检查免打扰是否启用
        
        Returns:
            是否启用
        """
        return self.config.get('enabled', False)
    
    def is_in_dnd_period(self) -> bool:
        """
        检查当前时间是否在免打扰时间段内
        
        Returns:
            是否在免打扰时间段
        """
        if not self.is_enabled():
            return False
        
        try:
            start_time = self.config.get('start_time', '23:00')
            end_time = self.config.get('end_time', '08:00')
            current_time = self.time_utils.get_current_shanghai_time_str()
            
            return self.time_utils.is_time_in_range(current_time, start_time, end_time)
            
        except Exception as e:
            logger.error(f"检查免打扰时间段时出错: {e}")
            return False
    
    def cache_message(self, message: str):
        """
        缓存消息
        
        Args:
            message: 消息内容
        """
        self.cached_messages.append(message)
        logger.debug(f"消息已缓存，当前缓存数量: {len(self.cached_messages)}")
    
    def cache_messages(self, messages: List[str]):
        """
        批量缓存消息
        
        Args:
            messages: 消息列表
        """
        self.cached_messages.extend(messages)
        logger.debug(f"批量消息已缓存，当前缓存数量: {len(self.cached_messages)}")
    
    def get_cached_messages(self) -> List[str]:
        """
        获取缓存的消息
        
        Returns:
            缓存的消息列表
        """
        return self.cached_messages
    
    def has_cached_messages(self) -> bool:
        """
        检查是否有缓存的消息
        
        Returns:
            是否有缓存
        """
        return len(self.cached_messages) > 0
    
    def get_cache_count(self) -> int:
        """
        获取缓存消息数量
        
        Returns:
            缓存数量
        """
        return len(self.cached_messages)
    
    def clear_cache(self):
        """清空缓存"""
        count = len(self.cached_messages)
        self.cached_messages.clear()
        logger.debug(f"缓存已清空，共 {count} 条消息")
    
    def should_cache_now(self) -> bool:
        """
        判断当前是否应该缓存消息而不是推送
        
        Returns:
            是否应该缓存
        """
        return self.is_in_dnd_period()
    
    def should_flush_cache(self) -> bool:
        """
        判断是否应该推送缓存的消息
        
        Returns:
            是否应该推送缓存
        """
        return not self.is_in_dnd_period() and self.has_cached_messages()
    
    def get_time_range(self) -> Dict[str, str]:
        """
        获取免打扰时间段配置
        
        Returns:
            时间段字典 {"start": "HH:MM", "end": "HH:MM"}
        """
        return {
            "start": self.config.get('start_time', '23:00'),
            "end": self.config.get('end_time', '08:00')
        }
