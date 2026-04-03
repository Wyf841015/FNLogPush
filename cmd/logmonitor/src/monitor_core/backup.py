#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份监控处理模块
处理备份操作的监控和推送
"""
import logging

logger = logging.getLogger(__name__)


class BackupMonitorHandler:
    """备份监控处理器"""
    
    def __init__(self, backup_monitor):
        """
        初始化备份监控处理器
        
        Args:
            backup_monitor: 备份监控服务实例
        """
        self.backup_monitor = backup_monitor
    
    def check_backup_operations(self):
        """
        检查新的备份操作记录
        """
        try:
            if not self.backup_monitor.is_enabled():
                return
            
            # 检查跟踪中的操作是否有状态变化
            changed_ops = self.backup_monitor.check_tracked_operations()
            if changed_ops:
                logger.info(f"发现 {len(changed_ops)} 条状态变化的备份操作")
                self.backup_monitor.process_operations(changed_ops)
            
            # 检查新的备份操作记录
            operations = self.backup_monitor.check_new_operations()
            if operations:
                logger.info(f"发现 {len(operations)} 条新的备份操作")
                self.backup_monitor.process_operations(operations)
        except Exception as e:
            logger.error(f"检查备份操作时出错: {e}")
