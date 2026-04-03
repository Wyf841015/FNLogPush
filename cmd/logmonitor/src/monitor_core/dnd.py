#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
免打扰处理模块
处理免打扰时间段的消息缓存和推送
"""
import logging
from typing import List

from utils.time_utils import TimeUtils

logger = logging.getLogger(__name__)


class DNDHandler:
    """免打扰处理器"""
    
    def __init__(self, dnd_service):
        """
        初始化免打扰处理器
        
        Args:
            dnd_service: 免打扰服务实例
        """
        self.dnd_service = dnd_service
        self.time_utils = TimeUtils()
    
    def check_dnd_cache(self, formatter, push_service, history_service, last_id,
                        push_coordinator=None):
        """
        检查是否需要推送免打扰缓存的消息

        Args:
            formatter:        消息格式化器实例
            push_service:     推送服务实例
            history_service:  历史记录服务实例
            last_id:          最后处理的日志ID
            push_coordinator: PushCoordinator 实例（优先使用，若传入则走协调器路径）
        """
        if self.dnd_service.should_flush_cache():
            cached_messages = self.dnd_service.get_cached_messages()
            if cached_messages:
                logger.info(f"退出免打扰时间段，推送缓存的 {len(cached_messages)} 条消息")
                self._push_cached_messages(
                    cached_messages, formatter, push_service,
                    history_service, last_id, push_coordinator
                )
    
    def _push_cached_messages(self, cached_messages: List[str], formatter,
                               push_service, history_service, last_id,
                               push_coordinator=None):
        """推送免打扰期间缓存的消息"""
        try:
            # 格式化汇总消息
            summary = formatter.format_dnd_summary(cached_messages)

            if push_coordinator is not None:
                # 优先走协调器（统一历史记录格式）
                push_coordinator.push_raw(summary, logs=[], last_id=last_id, count=len(cached_messages))
            else:
                # 兜底：直接调用 push_service（不记录历史）
                from config.manager import ConfigManager
                config_manager = ConfigManager()
                enabled_channels = config_manager.config.get('push_channels', {})
                success = push_service.push_message(summary, enabled_channels)

                from models.push_history import PushHistory
                history = PushHistory(
                    timestamp=self.time_utils.get_current_datetime_str(),
                    content=summary,
                    preview=summary,
                    success=success,
                    count=len(cached_messages),
                    last_id=last_id
                )
                history_service.add_history(history)

            # 清空缓存
            self.dnd_service.clear_cache()
            logger.info(f"成功推送免打扰缓存的 {len(cached_messages)} 条消息")

        except Exception as e:
            logger.error(f"推送免打扰缓存消息时出错: {e}")

