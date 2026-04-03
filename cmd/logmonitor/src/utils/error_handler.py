#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一异常处理模块
提供自定义异常类和统一的异常处理机制
"""
import logging
from functools import wraps
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)


class LogMonitorError(Exception):
    """日志监控基础异常类"""
    def __init__(self, message: str, code: int = 500, details: Optional[Dict] = None):
        """
        初始化异常
        
        Args:
            message: 异常消息
            code: 错误代码
            details: 详细信息
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class DatabaseError(LogMonitorError):
    """数据库异常"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 500, details)


class ConfigError(LogMonitorError):
    """配置异常"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 400, details)


class PushError(LogMonitorError):
    """推送异常"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 502, details)


class BackupError(LogMonitorError):
    """备份异常"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 500, details)


def error_handler(default_return: Any = None):
    """
    统一异常处理装饰器
    
    Args:
        default_return: 异常时的默认返回值
    
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except LogMonitorError as e:
                # 处理自定义异常
                logger.error(f"{func.__name__} 执行失败: {e.message}")
                if e.details:
                    logger.error(f"详细信息: {e.details}")
                return default_return
            except Exception as e:
                # 处理通用异常
                logger.error(f"{func.__name__} 执行失败: {str(e)}")
                logger.exception(e)  # 记录完整的异常堆栈
                return default_return
        return wrapper


def api_error_handler(func: Callable) -> Callable:
    """
    API异常处理装饰器
    
    Returns:
        装饰后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict) and 'success' not in result:
                return {"success": True, **result}
            return result
        except LogMonitorError as e:
            logger.error(f"API 执行失败: {e.message}")
            if e.details:
                logger.error(f"详细信息: {e.details}")
            return {
                "success": False,
                "error": e.message,
                "code": e.code,
                "details": e.details
            }
        except Exception as e:
            logger.error(f"API 执行失败: {str(e)}")
            logger.exception(e)  # 记录完整的异常堆栈
            return {
                "success": False,
                "error": str(e),
                "code": 500
            }
    return wrapper


def handle_exception(e: Exception) -> Dict[str, Any]:
    """
    处理异常并返回标准格式
    
    Args:
        e: 异常对象
    
    Returns:
        标准格式的错误响应
    """
    if isinstance(e, LogMonitorError):
        return {
            "success": False,
            "error": e.message,
            "code": e.code,
            "details": e.details
        }
    else:
        return {
            "success": False,
            "error": str(e),
            "code": 500
        }
