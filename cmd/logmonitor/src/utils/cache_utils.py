#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存工具模块
提供通用的内存缓存功能
"""
import time
import threading
import logging
from typing import Any, Optional, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器类"""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        初始化缓存管理器

        Args:
            default_ttl: 默认缓存过期时间（秒）
            max_size: 最大缓存项数量
        """
        self._cache: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期则返回None
        """
        with self._lock:
            if key not in self._cache:
                return None

            metadata = self._metadata.get(key)
            if metadata:
                if time.time() - metadata['timestamp'] > metadata.get('ttl', self._default_ttl):
                    # 缓存过期，删除
                    del self._cache[key]
                    del self._metadata[key]
                    return None

            return self._cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None则使用默认值
        """
        with self._lock:
            # 检查缓存大小
            if len(self._cache) >= self._max_size and key not in self._cache:
                # 删除最旧的缓存
                oldest_key = min(
                    self._metadata.keys(),
                    key=lambda k: self._metadata[k]['timestamp']
                )
                del self._cache[oldest_key]
                del self._metadata[oldest_key]

            # 设置缓存
            self._cache[key] = value
            self._metadata[key] = {
                'timestamp': time.time(),
                'ttl': ttl or self._default_ttl
            }

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._metadata[key]
                return True
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._metadata.clear()
            logger.info("缓存已清空")

    def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存项数量
        """
        with self._lock:
            expired_keys = []
            current_time = time.time()

            for key, metadata in self._metadata.items():
                if current_time - metadata['timestamp'] > metadata.get('ttl', self._default_ttl):
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                del self._metadata[key]

            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")

            return len(expired_keys)

    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'default_ttl': self._default_ttl
            }


# 全局缓存实例
_global_cache = CacheManager()


def cached(ttl: int = 300, key_prefix: str = ''):
    """
    缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀

    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}{func.__name__}_{str(args)}_{str(kwargs)}"

            # 尝试从缓存获取
            result = _global_cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            _global_cache.set(cache_key, result, ttl)
            return result

        # 添加清除缓存方法
        wrapper.clear_cache = lambda: _global_cache.delete(cache_key)
        return wrapper
    return decorator


def get_cache() -> CacheManager:
    """获取全局缓存实例"""
    return _global_cache
