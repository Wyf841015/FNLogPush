#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database服务模块
负责与SQLite数据库的交互
"""
import os
import sqlite3
import logging
import threading
import time
import queue
import hashlib
import sys
from typing import List, Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps

from utils.error_handler import DatabaseError

logger = logging.getLogger(__name__)


def retry_on_connection_error(max_retries: int = 3, delay: float = 0.5):
    """
    数据库连接错误重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
                    last_exception = e
                    if "locked" in str(e).lower() or "busy" in str(e).lower():
                        time.sleep(delay * (attempt + 1))
                        continue
                    raise
            raise last_exception
        return wrapper
    return decorator


class SQLiteConnectionPool:
    """SQLite连接池类（真正的连接池实现）"""

    def __init__(self, database_path: str, max_connections: int = 20):
        """
        初始化连接池

        Args:
            database_path: 数据库文件路径
            max_connections: 最大连接数（默认20，支持并发查询）
        """
        self.database_path = database_path
        self.max_connections = max_connections
        self._lock = threading.Lock()
        self._pool = queue.Queue(maxsize=max_connections)
        self._in_use: Dict[int, sqlite3.Connection] = {}  # 连接ID -> 连接对象
        self._connection_timestamps: Dict[int, float] = {}  # 连接ID -> 创建时间
        self._initialized = False

        # 预创建连接
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池，预创建连接"""
        if self._initialized:
            return

        try:
            for _ in range(self.max_connections):
                conn = self._create_connection()
                self._pool.put(conn)
            self._initialized = True
            logger.info(f"连接池初始化完成，创建了 {self.max_connections} 个连接")
        except Exception as e:
            logger.error(f"连接池初始化失败: {e}")
            raise

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接（只读模式）"""
        conn = sqlite3.connect(
            self.database_path,
            timeout=30.0,  # 增加超时时间
            isolation_level=None,  # 使用自动提交模式
            check_same_thread=False,
            uri=True  # 启用 URI 模式
        )
        conn.row_factory = sqlite3.Row
        # 只读模式配置：不启用 WAL 模式，因为需要写入权限
        # 只读模式下使用内存缓存提高查询性能
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn
    
    def get_connection(self, timeout: float = 10.0) -> sqlite3.Connection:
        """
        从连接池获取数据库连接

        Args:
            timeout: 获取连接的超时时间（秒，默认10秒）

        Returns:
            数据库连接对象

        Raises:
            queue.Empty: 连接池已空且超时
        """
        try:
            conn = self._pool.get(timeout=timeout)
            conn_id = id(conn)

            with self._lock:
                self._in_use[conn_id] = conn
                self._connection_timestamps[conn_id] = time.time()
                usage_percent = (len(self._in_use) / self.max_connections) * 100
                if usage_percent >= 80:
                    logger.warning(
                        f"数据库连接池使用率过高: {usage_percent:.1f}% "
                        f"({len(self._in_use)}/{self.max_connections})"
                    )

            # 检查连接是否有效
            if not self._is_connection_alive(conn):
                logger.warning("连接已失效，创建新连接")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = self._create_connection()
                with self._lock:
                    self._in_use[conn_id] = conn
                    self._connection_timestamps[conn_id] = time.time()

            logger.debug(f"获取连接 {conn_id}，当前使用中: {len(self._in_use)}/{self.max_connections}")
            return conn

        except queue.Empty:
            # 提供更详细的错误信息
            pool_status = self.get_pool_status()
            logger.error(
                f"连接池已空，等待超时 {timeout} 秒。"
                f"当前状态: 使用中={pool_status['in_use']}, "
                f"可用={pool_status['available']}, "
                f"最大={pool_status['max_connections']}"
            )
            raise DatabaseError(
                f"数据库连接池已满，请稍后重试。"
                f"当前使用: {pool_status['in_use']}/{pool_status['max_connections']}"
            )
    
    def _is_connection_alive(self, conn: sqlite3.Connection) -> bool:
        """检查连接是否有效"""
        try:
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def return_connection(self, conn: sqlite3.Connection):
        """
        返回连接到池

        Args:
            conn: 要返回的连接对象
        """
        if conn is None:
            return

        conn_id = id(conn)

        with self._lock:
            # 从使用中移除
            if conn_id in self._in_use:
                del self._in_use[conn_id]
            if conn_id in self._connection_timestamps:
                del self._connection_timestamps[conn_id]

        # 检查连接是否仍然有效
        if self._is_connection_alive(conn):
            try:
                self._pool.put_nowait(conn)
                logger.debug(f"归还连接 {conn_id}，当前使用中: {len(self._in_use)}/{self.max_connections}")
            except queue.Full:
                # 连接池已满，关闭连接
                try:
                    conn.close()
                    logger.debug(f"连接池已满，关闭连接 {conn_id}")
                except Exception:
                    pass
        else:
            # 连接已失效，关闭并创建新连接补充
            try:
                conn.close()
            except Exception:
                pass
            try:
                new_conn = self._create_connection()
                self._pool.put_nowait(new_conn)
                logger.debug(f"连接失效，创建新连接补充")
            except queue.Full:
                pass

    def close_connection(self):
        """关闭当前线程的连接（已废弃，保留兼容性）"""
        logger.warning("close_connection() 已废弃，连接由连接池统一管理")

    def close_all_connections(self):
        """关闭所有连接（用于清理）"""
        with self._lock:
            # 关闭所有使用中的连接
            for conn_id, conn in list(self._in_use.items()):
                try:
                    conn.close()
                except Exception:
                    pass
            self._in_use.clear()
            self._connection_timestamps.clear()

            # 关闭连接池中的所有连接
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Exception:
                    pass

            self._initialized = False
            logger.info("已关闭所有数据库连接")

    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态

        Returns:
            连接池状态信息
        """
        with self._lock:
            usage_percent = (len(self._in_use) / self.max_connections) * 100 if self.max_connections > 0 else 0

            return {
                "max_connections": self.max_connections,
                "in_use": len(self._in_use),
                "available": self._pool.qsize(),
                "initialized": self._initialized,
                "usage_percent": round(usage_percent, 2)
            }


class DatabaseService:
    """数据库服务类"""

    # 缓存配置
    CACHE_TTL = 300  # 缓存过期时间（秒）
    MAX_CACHE_SIZE = 100  # 最大缓存项数量
    MAX_CACHE_MEMORY_MB = 50  # 最大缓存内存（MB）
    CACHE_CLEAN_INTERVAL = 60  # 缓存清理间隔（秒）

    # 连接池配置
    DEFAULT_POOL_SIZE = 5  # 默认连接池大小（SQLite 并发写不需要大池，5 个连接足够）

    def __init__(self, database_path: str, pool_size: int = None):
        """
        初始化数据库服务

        Args:
            database_path: 数据库文件路径
            pool_size: 连接池大小（可选，默认5）
        """
        self.database_path = database_path
        pool_size = pool_size or self.DEFAULT_POOL_SIZE
        self.connection_pool = SQLiteConnectionPool(database_path, max_connections=pool_size)

        # 查询缓存
        self._cache = {}
        self._cache_metadata = {}
        self._cache_lock = threading.RLock()
        self._cache_cleaner_running = False
        self._stop_event = threading.Event()  # 用于优雅停止后台线程

        # 启动后台缓存清理线程
        self._start_cache_cleaner()
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接(上下文管理器)
        
        Yields:
            数据库连接对象
        """
        conn = self.connection_pool.get_connection()
        try:
            yield conn
        finally:
            self.connection_pool.return_connection(conn)
    
    def _generate_cache_key(self, method: str, *args, **kwargs) -> str:
        """
        生成缓存键（使用MD5哈希）

        Args:
            method: 方法名
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键字符串（MD5哈希）
        """
        key_data = f"{method}|{args}|{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _start_cache_cleaner(self):
        """启动后台缓存清理线程"""
        if self._cache_cleaner_running:
            return

        def clean_loop():
            # 使用 Event.wait() 代替 sleep，stop_event 被 set 后可立即退出
            while not self._stop_event.wait(timeout=self.CACHE_CLEAN_INTERVAL):
                self._clean_expired_cache()
                self._enforce_memory_limit()

        thread = threading.Thread(target=clean_loop, daemon=True, name="db-cache-cleaner")
        thread.start()
        self._cache_cleaner_running = True
        logger.info("缓存清理线程已启动")

    def shutdown(self):
        """关闭数据库服务，停止所有后台线程并释放连接池"""
        self._stop_event.set()
        self.connection_pool.close_all_connections()
        logger.info("数据库服务已关闭")
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期则返回None
        """
        with self._cache_lock:
            # 检查缓存是否存在
            if key not in self._cache:
                return None

            # 检查缓存是否过期
            metadata = self._cache_metadata.get(key)
            if metadata:
                if time.time() - metadata['timestamp'] > self.CACHE_TTL:
                    # 缓存过期，删除
                    del self._cache[key]
                    del self._cache_metadata[key]
                    return None

            return self._cache[key]
    
    def _set_cache(self, key: str, value: Any) -> None:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._cache_lock:
            # 估算新值的内存大小
            value_size = sys.getsizeof(value) / (1024 * 1024)  # MB

            # 计算当前缓存总内存
            current_memory = sum(sys.getsizeof(v) / (1024 * 1024) for v in self._cache.values())

            # 如果超过内存限制，清理最旧的缓存
            if current_memory + value_size > self.MAX_CACHE_MEMORY_MB:
                self._enforce_memory_limit(force_free=value_size)

            # 检查缓存数量限制
            if len(self._cache) >= self.MAX_CACHE_SIZE:
                # 删除最旧的缓存
                oldest_key = min(
                    self._cache_metadata.keys(),
                    key=lambda k: self._cache_metadata[k]['timestamp']
                )
                del self._cache[oldest_key]
                del self._cache_metadata[oldest_key]

            # 设置缓存
            self._cache[key] = value
            self._cache_metadata[key] = {
                'timestamp': time.time(),
                'size': value_size
            }

    def _enforce_memory_limit(self, force_free: float = 0):
        """
        强制执行内存限制

        Args:
            force_free: 需要强制释放的内存大小（MB）
        """
        with self._cache_lock:
            current_memory = sum(sys.getsizeof(v) / (1024 * 1024) for v in self._cache.values())
            target_memory = self.MAX_CACHE_MEMORY_MB - force_free

            # 如果当前内存超过目标，清理最旧的缓存
            if current_memory > target_memory:
                # 按时间排序，删除最旧的
                sorted_keys = sorted(
                    self._cache_metadata.keys(),
                    key=lambda k: self._cache_metadata[k]['timestamp']
                )

                for key in sorted_keys:
                    if current_memory <= target_memory:
                        break
                    # 先计算这个 key 的内存占用，再删除，避免删完后 get() 返回 0
                    item_size = sys.getsizeof(self._cache[key]) / (1024 * 1024)
                    del self._cache[key]
                    del self._cache_metadata[key]
                    current_memory -= item_size

                logger.debug(f"清理缓存以释放内存，当前: {current_memory:.2f}MB")
    
    def _clear_cache(self) -> None:
        """
        清空缓存
        """
        with self._cache_lock:
            self._cache.clear()
            self._cache_metadata.clear()
            logger.info("数据库查询缓存已清空")
    
    def _clean_expired_cache(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存项数量
        """
        with self._cache_lock:
            expired_keys = []
            current_time = time.time()

            for key, metadata in self._cache_metadata.items():
                if current_time - metadata['timestamp'] > self.CACHE_TTL:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]
                del self._cache_metadata[key]

            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")

            return len(expired_keys)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息
        """
        with self._cache_lock:
            total_memory = sum(sys.getsizeof(v) / (1024 * 1024) for v in self._cache.values())
            return {
                "cache_count": len(self._cache),
                "cache_max_count": self.MAX_CACHE_SIZE,
                "cache_memory_mb": round(total_memory, 2),
                "cache_max_memory_mb": self.MAX_CACHE_MEMORY_MB,
                "cache_ttl_seconds": self.CACHE_TTL
            }
    
    @retry_on_connection_error(max_retries=3, delay=0.3)
    def get_max_id(self) -> int:
        """
        获取日志表中的最大ID（不走缓存，保证准确性）
        
        Returns:
            最大ID，如果表为空返回0
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(id) FROM log")
                result = cursor.fetchone()
                max_id = result[0] if result[0] is not None else 0
                return max_id
        except sqlite3.Error as e:
            logger.error(f"获取最大ID时数据库错误: {e}")
            raise DatabaseError(f"获取最大ID失败: {e}")
    
    @retry_on_connection_error(max_retries=3, delay=0.3)
    def get_logs_after_id(self, last_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        获取指定ID之后的所有日志记录
        
        Args:
            last_id: 起始ID
            limit: 返回记录数限制
            
        Returns:
            日志记录字典列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 优化：只查询需要的字段，添加limit限制
                safe_limit = min(limit, 5000)
                query = """
                    SELECT id, logtime, loglevel, category, eventId, serviceId, uname, parameter
                    FROM log 
                    WHERE id > ? 
                    ORDER BY id ASC
                    LIMIT ?
                """
                cursor.execute(query, (last_id, safe_limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"查询日志时数据库错误: {e}")
            raise DatabaseError(f"查询日志失败: {e}")
    
    @retry_on_connection_error(max_retries=3, delay=0.3)
    def get_logs_by_filter(self, last_id: int, level_codes: List[int],
                          excluded_events: List[str], limit: int = 1000) -> List[Dict[str, Any]]:
        """
        根据过滤条件获取日志记录（监控轮询专用，不走缓存，确保实时性）

        Args:
            last_id: 起始ID
            level_codes: 日志级别代码列表
            excluded_events: 排除的事件ID列表
            limit: 返回记录数限制

        Returns:
            符合条件的日志记录字典列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = ["id > ?"]
                params = [last_id]

                # 优化日志级别过滤
                if level_codes:
                    if len(level_codes) <= 5:
                        placeholders = ','.join(['?'] * len(level_codes))
                        conditions.append(f"loglevel IN ({placeholders})")
                        params.extend(level_codes)
                    else:
                        min_level = min(level_codes)
                        max_level = max(level_codes)
                        conditions.append("loglevel BETWEEN ? AND ?")
                        params.extend([min_level, max_level])

                # 优化事件ID排除
                if excluded_events:
                    if len(excluded_events) <= 500:
                        placeholders = ','.join(['?'] * len(excluded_events))
                        conditions.append(f"(eventId IS NULL OR eventId NOT IN ({placeholders}))")
                        params.extend(excluded_events)

                # 构建最终查询（添加limit保护）
                safe_limit = min(limit, 5000)
                query = f"SELECT id, logtime, loglevel, category, eventId, serviceId, uname, parameter FROM log WHERE {' AND '.join(conditions)} ORDER BY id ASC LIMIT {safe_limit}"

                # 执行查询
                cursor.execute(query, params)

                # 使用生成器表达式转换结果
                result = [dict(row) for row in cursor.fetchall()]

                # 超大排除列表（>500）时，在 Python 层过滤
                if excluded_events and len(excluded_events) > 500:
                    excluded_set = set(excluded_events)
                    result = [
                        row for row in result
                        if row.get('eventId') is None or row.get('eventId') not in excluded_set
                    ]

                return result
        except sqlite3.Error as e:
            logger.error(f"查询过滤日志时数据库错误: {e}")
            raise DatabaseError(f"查询过滤日志失败: {e}")
    
    def check_connection(self) -> bool:
        """
        检查数据库连接是否正常

        Returns:
            是否连接成功
        """
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False
    
    @retry_on_connection_error(max_retries=2)
    def create_indexes(self) -> bool:
        """
        创建数据库索引以提高查询性能
        注意：在只读数据库上会跳过索引创建，不会报错

        Returns:
            是否创建成功（只读数据库返回 True）
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 批量创建索引（使用事务）
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_log_id ON log(id)",
                    "CREATE INDEX IF NOT EXISTS idx_log_loglevel ON log(loglevel)",
                    "CREATE INDEX IF NOT EXISTS idx_log_eventId ON log(eventId)",
                    "CREATE INDEX IF NOT EXISTS idx_log_logtime ON log(logtime)"
                ]

                for idx_sql in indexes:
                    cursor.execute(idx_sql)

                conn.commit()
                logger.info("数据库索引创建成功")
                return True
        except sqlite3.OperationalError as e:
            # 检查是否是只读数据库错误
            if "readonly" in str(e).lower():
                logger.info("检测到只读数据库，跳过索引创建")
                return True
            # 其他错误继续抛出
            logger.error(f"创建数据库索引时数据库错误: {e}")
            raise DatabaseError(f"创建索引失败: {e}")
        except sqlite3.Error as e:
            logger.error(f"创建数据库索引时数据库错误: {e}")
            raise DatabaseError(f"创建索引失败: {e}")
    
    @retry_on_connection_error(max_retries=2)
    def get_table_info(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取日志表的结构信息
        
        Returns:
            表字段信息列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(log)")
                columns = cursor.fetchall()
                return [{"id": c[0], "name": c[1], "type": c[2]} for c in columns]
        except sqlite3.Error as e:
            logger.error(f"获取表信息时数据库错误: {e}")
            raise DatabaseError(f"获取表信息失败: {e}")
    
    @retry_on_connection_error(max_retries=2)
    def get_total_count(self) -> int:
        """
        获取日志记录总数
        
        Returns:
            记录总数
        """
        cache_key = self._generate_cache_key('get_total_count')
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM log")
                count = cursor.fetchone()[0]
                self._set_cache(cache_key, count)
                return count
        except sqlite3.Error as e:
            logger.error(f"获取记录总数时数据库错误: {e}")
            raise DatabaseError(f"获取记录总数失败: {e}")
    
    @retry_on_connection_error(max_retries=2)
    def get_recent_logs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近的日志记录

        Args:
            limit: 返回记录数量

        Returns:
            日志记录列表
        """
        cache_key = self._generate_cache_key('get_recent_logs', limit)
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                safe_limit = min(limit, 100)
                cursor.execute("SELECT id, logtime, loglevel, category, eventId, serviceId, uname, parameter FROM log ORDER BY id DESC LIMIT ?", (safe_limit,))
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
                self._set_cache(cache_key, result)
                return result
        except sqlite3.Error as e:
            logger.error(f"获取最近日志时数据库错误: {e}")
            raise DatabaseError(f"获取最近日志失败: {e}")

    @retry_on_connection_error(max_retries=2)
    def get_event_id_statistics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取事件ID统计信息

        Args:
            limit: 返回记录数量限制

        Returns:
            事件ID统计列表，按数量降序排列
            格式: [{"event_id": "LoginSucc", "count": 100}, ...]
        """
        cache_key = self._generate_cache_key('get_event_id_statistics', limit)
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                safe_limit = min(limit, 1000)
                cursor.execute("""
                    SELECT eventId, COUNT(*) as count
                    FROM log
                    WHERE eventId IS NOT NULL AND eventId != ''
                    GROUP BY eventId
                    ORDER BY count DESC
                    LIMIT ?
                """, (safe_limit,))
                rows = cursor.fetchall()
                result = [{"event_id": row[0], "count": row[1]} for row in rows]
                self._set_cache(cache_key, result)
                return result
        except sqlite3.Error as e:
            logger.error(f"获取事件ID统计时数据库错误: {e}")
            raise DatabaseError(f"获取事件ID统计失败: {e}")

    @retry_on_connection_error(max_retries=2)
    def get_new_event_ids(self, known_event_ids: List[str], limit: int = 100) -> List[str]:
        """
        获取数据库中存在但不在已知列表中的新事件ID

        Args:
            known_event_ids: 已知的事件ID列表
            limit: 返回记录数量限制

        Returns:
            新出现的事件ID列表
        """
        sorted_known_ids = sorted(known_event_ids) if known_event_ids else []
        cache_key = self._generate_cache_key('get_new_event_ids', tuple(sorted_known_ids), limit)
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                safe_limit = min(limit, 1000)
                cursor.execute("""
                    SELECT DISTINCT eventId
                    FROM log
                    WHERE eventId IS NOT NULL AND eventId != ''
                    LIMIT ?
                """, (safe_limit,))
                rows = cursor.fetchall()
                all_event_ids = set(row[0] for row in rows)
                known_ids = set(known_event_ids)
                new_event_ids = sorted(list(all_event_ids - known_ids))
                self._set_cache(cache_key, new_event_ids)
                return new_event_ids
        except sqlite3.Error as e:
            logger.error(f"获取新事件ID时数据库错误: {e}")
            raise DatabaseError(f"获取新事件ID失败: {e}")

    @retry_on_connection_error(max_retries=2)
    def get_event_id_list(self, limit: int = 100) -> List[str]:
        """
        获取数据库中所有事件ID列表

        Args:
            limit: 返回记录数量限制

        Returns:
            事件ID列表（去重）
        """
        cache_key = self._generate_cache_key('get_event_id_list', limit)
        cached_result = self._get_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                safe_limit = min(limit, 1000)
                cursor.execute("""
                    SELECT DISTINCT eventId
                    FROM log
                    WHERE eventId IS NOT NULL AND eventId != ''
                    ORDER BY eventId
                    LIMIT ?
                """, (safe_limit,))
                rows = cursor.fetchall()
                result = [row[0] for row in rows]
                self._set_cache(cache_key, result)
                return result
        except sqlite3.Error as e:
            logger.error(f"获取事件ID列表时数据库错误: {e}")
            raise DatabaseError(f"获取事件ID列表失败: {e}")



    def health_check(self) -> Dict[str, Any]:
        """
        数据库健康检查

        Returns:
            健康状态字典
        """
        try:
            # 检查连接是否存活
            connection_alive = False
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 检查表是否存在
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='log'
                """)
                table_exists = cursor.fetchone() is not None

                # 获取记录数
                record_count = 0
                if table_exists:
                    cursor.execute("SELECT COUNT(*) FROM log")
                    record_count = cursor.fetchone()[0]

                # 检查连接是否存活
                connection_alive = self.connection_pool._is_connection_alive(conn)

            # 获取数据库文件大小
            db_size = 0
            if os.path.exists(self.database_path):
                db_size = os.path.getsize(self.database_path)

            return {
                "status": "healthy",
                "table_exists": table_exists,
                "record_count": record_count,
                "db_size_bytes": db_size,
                "connection_alive": connection_alive
            }
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def reconnect(self) -> bool:
        """
        手动重新连接数据库

        Returns:
            是否重连成功
        """
        try:
            self.close_connection()
            conn = self.connection_pool._create_connection()
            self.local.connection = conn
            logger.info("数据库重连成功")
            return True
        except Exception as e:
            logger.error(f"数据库重连失败: {e}")
            return False
