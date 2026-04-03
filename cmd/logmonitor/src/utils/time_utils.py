#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间工具模块
"""
import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pytz

logger = logging.getLogger(__name__)

# UTC+8 固定偏移（上海/北京时间），不依赖任何时区数据库
_TZ_CST = timezone(timedelta(hours=8))


class TimeUtils:
    """时间工具类"""

    @staticmethod
    def timestamp_to_shanghai(timestamp: int) -> str:
        """
        将时间戳转换为本地时间字符串

        Args:
            timestamp: 时间戳(秒或毫秒)

        Returns:
            格式化的本地时间字符串
        """
        try:
            # 判断时间戳是秒还是毫秒
            if timestamp > 10_000_000_000:
                timestamp = int(timestamp / 1000)

            # 使用本地时区（与备份数据库保持一致）
            utc_dt =datetime.fromtimestamp(timestamp, timezone.utc)+timedelta(hours=8)
            dt=utc_dt.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
            return dt

        except Exception as e:
            logger.error(f"时间转换错误: {e}, timestamp: {timestamp}")
            return "时间转换错误"

    @staticmethod
    def is_time_in_range(current_time: str, start_time: str, end_time: str) -> bool:
        """
        检查当前时间是否在指定时间段内
        
        Args:
            current_time: 当前时间 (HH:MM格式)
            start_time: 开始时间 (HH:MM格式)
            end_time: 结束时间 (HH:MM格式)
            
        Returns:
            是否在时间段内
        """
        try:
            # 解析时间
            start_h, start_m = map(int, start_time.split(':'))
            end_h, end_m = map(int, end_time.split(':'))
            current_h, current_m = map(int, current_time.split(':'))
            
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            current_minutes = current_h * 60 + current_m
            
            # 如果结束时间小于开始时间，表示跨天(如23:00-08:00)
            if end_minutes < start_minutes:
                return current_minutes >= start_minutes or current_minutes < end_minutes
            else:
                return start_minutes <= current_minutes < end_minutes
                
        except Exception as e:
            logger.error(f"时间范围检查错误: {e}")
            return False
    
    @staticmethod
    def get_current_shanghai_time_str() -> str:
        """
        获取当前本地时间字符串

        Returns:
            当前时间字符串 (HH:MM格式)
        """
        return datetime.now(_TZ_CST).strftime('%H:%M')

    @staticmethod
    def get_current_datetime_str() -> str:
        """
        获取当前日期时间字符串

        Returns:
            日期时间字符串 (YYYY-MM-DD HH:MM:SS格式)
        """
        return datetime.now(_TZ_CST).strftime('%Y-%m-%d %H:%M:%S')
