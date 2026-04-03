#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录服务模块
负责推送历史的管理

存储后端：SQLite（push_history.db）
  - 取代原有的 push_history.json，解决高并发写入竞争和无限增长问题
  - 启动时自动将旧 push_history.json 迁移到 SQLite
  - 对外接口保持不变，调用方无需改动
"""
import json
import logging
import os
import sqlite3
import threading
from collections import deque
from typing import List, Optional

from models.push_history import PushHistory

logger = logging.getLogger(__name__)

# SQLite 数据库文件名（与旧 JSON 文件同目录）
_DB_NAME = 'push_history.db'


class HistoryService:
    """历史记录服务类（SQLite 存储后端）"""

    def __init__(self, history_file: str = 'push_history.json', max_size: int = 1000):
        """
        初始化历史记录服务

        Args:
            history_file: 旧 JSON 文件路径（仅用于迁移，迁移后不再写入）
            max_size: 最大历史记录数量（超出后自动裁剪最旧记录）
        """
        self.history_file = history_file
        self.max_size = max_size
        self.lock = threading.Lock()

        # SQLite 文件放在与 history_file 相同目录
        base_dir = os.path.dirname(os.path.abspath(history_file)) if os.path.dirname(history_file) else '.'
        self.db_path = os.path.join(base_dir, _DB_NAME)

        self._init_db()
        self._migrate_from_json()

    # ------------------------------------------------------------------
    # 内部：数据库初始化与迁移
    # ------------------------------------------------------------------

    def _init_db(self):
        """建表（若不存在）"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS push_history (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT    NOT NULL,
                    content   TEXT    NOT NULL DEFAULT '',
                    preview   TEXT    NOT NULL DEFAULT '',
                    success   INTEGER NOT NULL DEFAULT 0,
                    count     INTEGER NOT NULL DEFAULT 0,
                    last_id   INTEGER NOT NULL DEFAULT 0,
                    levels    TEXT,
                    source    TEXT    NOT NULL DEFAULT 'log',
                    channel_results TEXT
                )
            """)
            # 加索引加速时间排序查询
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_push_history_id ON push_history(id DESC)"
            )
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """获取 SQLite 连接（check_same_thread=False，由 self.lock 保护并发）"""
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _migrate_from_json(self):
        """将旧 push_history.json 迁移到 SQLite（仅执行一次）"""
        if not os.path.exists(self.history_file):
            return

        # 检查 SQLite 里是否已有数据（避免重复迁移）
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM push_history").fetchone()[0]
            if count > 0:
                logger.debug("push_history.db 已有数据，跳过 JSON 迁移")
                return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            if not history_data:
                return

            migrated = 0
            with self._get_conn() as conn:
                for item in history_data:
                    try:
                        conn.execute(
                            "INSERT INTO push_history "
                            "(timestamp, content, preview, success, count, last_id, levels, source) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                item.get('timestamp', ''),
                                item.get('content', ''),
                                item.get('preview', ''),
                                1 if item.get('success', False) else 0,
                                item.get('count', 0),
                                item.get('last_id', 0),
                                json.dumps(item['levels']) if item.get('levels') else None,
                                item.get('source', 'log'),
                            )
                        )
                        migrated += 1
                    except Exception as e:
                        logger.warning(f"迁移单条历史记录失败: {e}")
                conn.commit()

            logger.info(f"push_history.json 迁移完成，共迁移 {migrated} 条记录")

            # 迁移成功后重命名旧文件（保留备份，不删除）
            backup_path = self.history_file + '.migrated'
            os.rename(self.history_file, backup_path)
            logger.info(f"旧 JSON 文件已重命名为: {backup_path}")

        except Exception as e:
            logger.error(f"迁移 push_history.json 时出错: {e}")

    def _trim_to_max_size(self, conn: sqlite3.Connection):
        """若记录超过 max_size，删除最旧的超出部分"""
        count = conn.execute("SELECT COUNT(*) FROM push_history").fetchone()[0]
        if count > self.max_size:
            excess = count - self.max_size
            conn.execute(
                "DELETE FROM push_history WHERE id IN "
                "(SELECT id FROM push_history ORDER BY id ASC LIMIT ?)",
                (excess,)
            )

    # ------------------------------------------------------------------
    # 公共接口（与原 HistoryService 保持完全兼容）
    # ------------------------------------------------------------------

    def add_history(self, history: PushHistory):
        """
        添加历史记录

        Args:
            history: 历史记录对象
        """
        levels_json = json.dumps(history.levels) if history.levels is not None else None
        channel_results_json = json.dumps(history.channel_results) if history.channel_results is not None else None

        with self.lock:
            try:
                with self._get_conn() as conn:
                    conn.execute(
                        "INSERT INTO push_history "
                        "(timestamp, content, preview, success, count, last_id, levels, source, channel_results) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            history.timestamp,
                            history.content,
                            history.preview,
                            1 if history.success else 0,
                            history.count,
                            history.last_id,
                            levels_json,
                            history.source,
                            channel_results_json,
                        )
                    )
                    self._trim_to_max_size(conn)
                    conn.commit()
            except Exception as e:
                logger.error(f"写入推送历史失败: {e}")

    def get_recent_history(self, limit: int = 20, offset: int = 0, start_date: str = None, end_date: str = None) -> List[PushHistory]:
        """
        获取最近的历史记录（按时间倒序），支持分页和日期筛选

        Args:
            limit: 返回数量限制
            offset: 偏移量（用于分页）
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)

        Returns:
            历史记录列表
        """
        try:
            with self._get_conn() as conn:
                query = "SELECT * FROM push_history"
                params = []

                # 添加日期筛选条件
                if start_date or end_date:
                    conditions = []
                    if start_date:
                        conditions.append("date(timestamp) >= ?")
                        params.append(start_date)
                    if end_date:
                        conditions.append("date(timestamp) <= ?")
                        params.append(end_date)
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                rows = conn.execute(query, params).fetchall()

            result = []
            for i, row in enumerate(rows):
                item = self._row_to_push_history(row)
                item.index = offset + i
                result.append(item)
            return result
        except Exception as e:
            logger.error(f"查询推送历史失败: {e}")
            return []

    def get_history_by_id(self, history_id: int) -> Optional[PushHistory]:
        """
        根据索引（倒序位置）获取历史记录

        Args:
            history_id: 历史记录索引（0 = 最新）

        Returns:
            历史记录对象或 None
        """
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM push_history ORDER BY id DESC LIMIT 1 OFFSET ?",
                    (history_id,)
                ).fetchone()

            if row:
                item = self._row_to_push_history(row)
                item.index = history_id
                return item
            return None
        except Exception as e:
            logger.error(f"按索引查询推送历史失败: {e}")
            return None

    def get_last_id(self) -> int:
        """
        获取最后处理的日志 ID

        Returns:
            最后 ID，如果没有历史记录返回 0
        """
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT last_id FROM push_history ORDER BY id DESC LIMIT 1"
                ).fetchone()
            return row['last_id'] if row else 0
        except Exception as e:
            logger.error(f"查询最后日志 ID 失败: {e}")
            return 0

    def clear_history(self):
        """清空历史记录"""
        with self.lock:
            try:
                with self._get_conn() as conn:
                    conn.execute("DELETE FROM push_history")
                    conn.commit()
                logger.info("推送历史记录已清空")
            except Exception as e:
                logger.error(f"清空推送历史失败: {e}")

    def get_count(self, start_date: str = None, end_date: str = None) -> int:
        """
        获取历史记录数量，支持日期筛选

        Args:
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)

        Returns:
            历史记录数量
        """
        try:
            with self._get_conn() as conn:
                query = "SELECT COUNT(*) FROM push_history"
                params = []

                # 添加日期筛选条件
                if start_date or end_date:
                    conditions = []
                    if start_date:
                        conditions.append("date(timestamp) >= ?")
                        params.append(start_date)
                    if end_date:
                        conditions.append("date(timestamp) <= ?")
                        params.append(end_date)
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)

                return conn.execute(query, params).fetchone()[0]
        except Exception as e:
            logger.error(f"查询历史记录数量失败: {e}")
            return 0

    def get_last_timestamp(self) -> Optional[str]:
        """
        获取最后一条历史记录的时间戳

        Returns:
            时间戳字符串或 None
        """
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT timestamp FROM push_history ORDER BY id DESC LIMIT 1"
                ).fetchone()
            return row['timestamp'] if row else None
        except Exception as e:
            logger.error(f"查询最后时间戳失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_push_history(row: sqlite3.Row) -> PushHistory:
        """将 SQLite Row 转换为 PushHistory 对象"""
        levels = None
        if row['levels']:
            try:
                levels = json.loads(row['levels'])
            except Exception:
                pass

        channel_results = None
        if row['channel_results']:
            try:
                channel_results = json.loads(row['channel_results'])
            except Exception:
                pass

        return PushHistory(
            timestamp=row['timestamp'],
            content=row['content'],
            preview=row['preview'],
            success=bool(row['success']),
            count=row['count'],
            last_id=row['last_id'],
            levels=levels,
            source=row['source'],
            channel_results=channel_results,
        )

    # ------------------------------------------------------------------
    # 兼容旧代码的属性（read-only，不再维护内存 deque）
    # ------------------------------------------------------------------

    @property
    def history(self) -> deque:
        """向后兼容：返回当前全量历史记录的内存快照（不推荐直接使用）"""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM push_history ORDER BY id ASC"
                ).fetchall()
            d = deque(maxlen=self.max_size)
            for row in rows:
                d.append(self._row_to_push_history(row))
            return d
        except Exception as e:
            logger.error(f"读取全量历史记录失败: {e}")
            return deque(maxlen=self.max_size)
