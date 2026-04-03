#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份监控服务模块
负责监控 basic_backup.db3 数据库中的 operations 表
"""
import sqlite3
import logging
import os
import threading
import time
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime

from models.backup_operation import BackupOperation, OPERATION_STATUS_MAP
from utils.time_utils import TimeUtils

logger = logging.getLogger(__name__)


class BackupConnectionPool:
    """备份数据库连接池"""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self.local = threading.local()

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接（只读模式）"""
        conn = sqlite3.connect(
            self.database_path,
            timeout=30.0,
            check_same_thread=False,
            uri=True  # 启用 URI 模式以支持只读
        )
        conn.row_factory = sqlite3.Row
        # 只读模式：不启用 WAL 模式，避免写入操作
        return conn

    def get_connection(self) -> sqlite3.Connection:
        thread_id = threading.get_ident()
        if not hasattr(self.local, 'connection'):
            conn = self._create_connection()
            self.local.connection = conn
            logger.debug(f"创建备份数据库新连接 (线程: {thread_id})")
            return conn

        conn = self.local.connection
        try:
            conn.execute("SELECT 1")
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = self._create_connection()
            self.local.connection = conn
            logger.info("备份数据库连接已重新建立")
            return conn


class BackupDatabaseService:
    """备份数据库服务类"""

    def __init__(self, database_path: str):
        """
        初始化备份数据库服务

        Args:
            database_path: 数据库文件路径
        """
        self.database_path = database_path
        self._pool = BackupConnectionPool(database_path)

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接(上下文管理器)

        Yields:
            数据库连接对象
        """
        conn = self._pool.get_connection()
        try:
            yield conn
        finally:
            pass  # 连接由池管理，不需要关闭
    
    def check_connection(self) -> bool:
        """
        检查数据库连接是否正常
        
        Returns:
            是否连接成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"备份数据库连接检查失败: {e}")
            return False
    
    def get_max_operation_id(self) -> int:
        """
        获取operations表中的最大ID
        
        Returns:
            最大ID，如果表为空返回0
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(id) FROM operations")
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except Exception as e:
            logger.error(f"获取备份操作最大ID时出错: {e}")
            return 0
    
    def get_max_start_time(self) -> int:
        """
        获取operations表中的最大start_time
        
        Returns:
            最大start_time，如果表为空返回0
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(start_time) FROM operations")
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except Exception as e:
            logger.error(f"获取备份操作最新时间时出错: {e}")
            return 0
    
    def get_operations_after_time(self, last_time: int, status_filter: List[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定时间之后的操作记录
        
        Args:
            last_time: 起始时间戳
            status_filter: 状态过滤列表（只返回这些状态的记录）
            
        Returns:
            操作记录字典列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 使用 > 以确保不重复查询已处理过的记录
                # 同时按 start_time 和 id 排序确保顺序一致
                if status_filter:
                    placeholders = ','.join(['?'] * len(status_filter))
                    query = f"""
                        SELECT * FROM operations
                        WHERE start_time > ? AND status IN ({placeholders})
                        ORDER BY start_time ASC, id ASC
                    """
                    cursor.execute(query, [last_time] + status_filter)
                else:
                    query = """
                        SELECT * FROM operations
                        WHERE start_time > ?
                        ORDER BY start_time ASC, id ASC
                    """
                    cursor.execute(query, (last_time,))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取备份操作记录时出错: {e}")
            return []
    
    def get_operation_by_id(self, operation_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单条操作记录
        
        Args:
            operation_id: 操作记录ID
            
        Returns:
            操作记录字典，如果不存在返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM operations WHERE id = ?", (operation_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取操作记录时出错: {e}")
            return None
    
    def get_operations_after_id(self, last_id: int, status_filter: List[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定ID之后的操作记录
        
        Args:
            last_id: 起始ID
            status_filter: 状态过滤列表（只返回这些状态的记录）
            
        Returns:
            操作记录字典列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if status_filter:
                    placeholders = ','.join(['?'] * len(status_filter))
                    query = f"""
                        SELECT * FROM operations 
                        WHERE id > ? AND status IN ({placeholders})
                        ORDER BY id ASC
                    """
                    cursor.execute(query, [last_id] + status_filter)
                else:
                    query = """
                        SELECT * FROM operations 
                        WHERE id > ?
                        ORDER BY id ASC
                    """
                    cursor.execute(query, (last_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"查询备份操作记录时出错: {e}")
            return []
    
    def get_task_info(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取任务信息时出错: {e}")
            return None
    
    def get_storage_info(self, storage_id: int) -> Optional[Dict[str, Any]]:
        """
        获取存储信息
        
        Args:
            storage_id: 存储ID
            
        Returns:
            存储信息字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM storages WHERE id = ?", (storage_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取存储信息时出错: {e}")
            return None
    
    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的操作记录
        
        Args:
            limit: 返回记录数量
            
        Returns:
            操作记录列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM operations 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取最近备份操作时出错: {e}")
            return []


class BackupMonitorService:
    """备份监控服务类"""
    
    def __init__(self, config: Dict[str, Any], push_service, history_service, dnd_service=None):
        """
        初始化备份监控服务
        
        Args:
            config: 配置字典
            push_service: 推送服务实例
            history_service: 历史记录服务实例
            dnd_service: 免打扰服务实例（可选）
        """
        self.config = config
        self.push_service = push_service
        self.history_service = history_service
        self.dnd_service = dnd_service
        
        # 备份数据库服务
        self.backup_db_service = None
        self.backup_db_available = False
        
        # 监控状态 - 使用start_time作为监控基准
        self.last_start_time = 0
        self.running = False
        
        # 跟踪中的操作 {operation_id: BackupOperation}
        self.tracking_operations = {}
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化备份数据库连接"""
        backup_config = self.config.get('backup_monitor', {})
        db_path = backup_config.get('database_path', '')
        
        if not db_path:
            logger.info("备份数据库路径未配置")
            return
        
        if not os.path.exists(db_path):
            logger.warning(f"备份数据库文件不存在: {db_path}")
            return
        
        self.backup_db_service = BackupDatabaseService(db_path)
        if self.backup_db_service.check_connection():
            self.backup_db_available = True
            # 检查是否需要扫描历史记录
            scan_history = backup_config.get('scan_history', False)
            if scan_history:
                # 扫描最近1小时的历史记录
                self.last_start_time = int(time.time()) - 3600
                logger.info(f"备份数据库已连接: {db_path}, 扫描历史模式, 初始时间: {self.last_start_time}")
            else:
                # 初始化为数据库最大时间，启动后只推送新记录
                max_time = self.backup_db_service.get_max_start_time()
                self.last_start_time = max_time if max_time > 0 else 0
                logger.info(f"备份数据库已连接: {db_path}, 初始时间: {self.last_start_time}")
        else:
            logger.error(f"备份数据库连接失败: {db_path}")
    
    def update_config(self, new_config: Dict[str, Any], dnd_service=None):
        """
        更新配置
        
        Args:
            new_config: 新的配置项
            dnd_service: 免打扰服务实例（可选）
        """
        self.config = new_config
        
        # 更新免打扰服务
        if dnd_service:
            self.dnd_service = dnd_service
        
        # 检查是否需要重新初始化数据库
        if 'backup_monitor' in new_config:
            old_path = self.backup_db_service.database_path if self.backup_db_service else ''
            new_path = new_config.get('backup_monitor', {}).get('database_path', '')
            
            # 如果路径改变或数据库未初始化，则重新初始化
            if new_path != old_path or not self.backup_db_service or not self.backup_db_available:
                self._init_database()
    
    def is_enabled(self) -> bool:
        """检查备份监控是否启用"""
        backup_config = self.config.get('backup_monitor', {})
        return backup_config.get('enabled', False)
    
    def check_new_operations(self) -> List[BackupOperation]:
        """
        检查新的备份操作记录
        
        Returns:
            新的备份操作列表
        """
        if not self.backup_db_available or self.backup_db_service is None:
            return []
        
        if not self.is_enabled():
            return []
        
        try:
            # 获取状态过滤配置
            backup_config = self.config.get('backup_monitor', {})
            status_filter = backup_config.get('status_filter', [1, 2, 3, 4])  # 默认：开始、进行中、成功、失败

            # 查询新记录 - 基于start_time查询
            rows = self.backup_db_service.get_operations_after_time(
                self.last_start_time,
                status_filter
            )
            
            operations = []
            max_time = self.last_start_time
            
            for row in rows:
                operation = BackupOperation.from_dict(row)
                operations.append(operation)
                # 使用start_time更新基准时间
                if operation.start_time and operation.start_time > max_time:
                    max_time = operation.start_time
            
            logger.debug(f"检查到 {len(operations)} 条新备份操作")

            # 如果有查询结果，更新last_start_time为最新记录的时间
            if rows:
                self.last_start_time = max_time
                logger.info(f"更新备份操作最后时间: {self.last_start_time}")
            
            # 过滤掉已经在跟踪列表中的操作，避免与check_tracked_operations重复推送
            operations_to_return = []
            for op in operations:
                # 检查是否已经在跟踪列表中
                if op.id in self.tracking_operations:
                    logger.debug(f"操作 ID={op.id} 已在跟踪列表中，跳过")
                    continue
                
                # 检查是否有status=1(开始)的记录，需要立即推送并跟踪
                if op.status == 1:
                    # 立即推送并加入跟踪
                    self._push_and_track_operation(op)
                else:
                    operations_to_return.append(op)
            
            # 返回非status=1且未跟踪的记录
            return operations_to_return
            
        except Exception as e:
            logger.error(f"检查备份操作时出错: {e}")
            return []
    
    def _push_and_track_operation(self, operation: BackupOperation):
        """
        立即推送操作并开始跟踪
        
        Args:
            operation: 备份操作记录
        """
        # 加入跟踪列表
        self.tracking_operations[operation.id] = operation
        logger.info(f"开始跟踪操作 ID={operation.id}, status={operation.status}")
        
        # 立即推送
        content = self.format_operation_message(operation)
        
        # 检查免打扰
        if self.dnd_service and self.dnd_service.should_cache_now():
            logger.info("在免打扰时间段，缓存开始状态消息")
            self.dnd_service.cache_message(content)
            return
        
        # 推送
        enabled_channels = self.config.get('push_channels', {})
        success = self.push_service.push_message(content, enabled_channels)
        
        # 记录到推送历史
        from models.push_history import PushHistory
        from utils.time_utils import TimeUtils
        task_info = self.backup_db_service.get_task_info(operation.task_id) if self.backup_db_service else None
        task_name = task_info.get('name', '未知任务') if task_info else '未知任务'
        preview = f"{operation.get_start_time_str()} {task_name} {operation.get_status_name()}"
        
        history = PushHistory(
            timestamp=TimeUtils.get_current_datetime_str(),
            content=content,
            preview=preview,
            success=success,
            count=1,
            last_id=operation.start_time,
            source='backup'
        )
        self.history_service.add_history(history)
        
        logger.info(f"已推送并跟踪操作 ID={operation.id}")
    
    def check_tracked_operations(self) -> List[BackupOperation]:
        """
        检查跟踪中的操作是否有状态变化
        
        Returns:
            状态发生变化的备份操作列表
        """
        if not self.tracking_operations:
            return []
        
        if not self.backup_db_available or self.backup_db_service is None:
            return []
        
        try:
            changed_operations = []
            completed_ids = []  # 已完成的操作ID
            
            for op_id, tracked_op in list(self.tracking_operations.items()):
                # 从数据库获取最新状态
                row = self.backup_db_service.get_operation_by_id(op_id)
                if not row:
                    continue
                
                current_op = BackupOperation.from_dict(row)
                old_status = tracked_op.status
                new_status = current_op.status
                
                # 检查状态是否变化
                if old_status != new_status:
                    logger.info(f"操作 ID={op_id} 状态变化: {old_status} -> {new_status}")
                    changed_operations.append(current_op)
                    
                    # 如果是终态(2=取消，3=成功, 4=失败, 5=已取消)，停止跟踪
                    if new_status in [2, 3, 4, 5]:
                        completed_ids.append(op_id)
            
            # 移除已完成的操作
            for op_id in completed_ids:
                del self.tracking_operations[op_id]
                logger.info(f"操作 ID={op_id} 已完成，停止跟踪")
            
            return changed_operations
            
        except Exception as e:
            logger.error(f"检查跟踪操作时出错: {e}")
            return []
    
    def format_operation_message(self, operation: BackupOperation) -> str:
        """
        格式化操作消息
        
        Args:
            operation: 备份操作记录
            
        Returns:
            格式化的消息字符串
        """
        # 获取任务信息
        task_info = None
        if self.backup_db_service:
            task_info = self.backup_db_service.get_task_info(operation.task_id)
        
        task_name = task_info.get('name', '未知任务') if task_info else '未知任务'
        direction = task_info.get('direction', 0) if task_info else 0
        direction_name = "上传" if direction == 0 else "下载"
        
        status_name = operation.get_status_name()
        status_emoji = {
            1: "🚀",  # 开始
            2: "🔄",  # 进行中
            3: "✅",  # 成功
            4: "❌",  # 失败
            5: "🚫",  # 未知
            0: "❓"   # 未知
        }.get(operation.status, "❓")
        
        # 构建消息（不使用markdown格式）
        backup_icon = "💾"  # 数据库备份图标
        lines = [
            f"{backup_icon} {status_emoji} {task_name}备份任务{status_name}",
            "",
            f"📋 任务名称: {task_name}",
            f"🔄 操作类型: {direction_name}",
            f"📌 任务状态: {status_name}",
            f"🕐 开始时间: {operation.get_start_time_str()}",
        ]
        
        if operation.status in [3, 4]:  # 已完成或失败
            lines.append(f"⏰ 结束时间: {operation.get_finished_time_str()}")
            lines.append(f"⏳ 实际耗时: {operation.format_duration()}")
            
        if operation.files_count > 0:
            lines.append(f"📁 文件总数: {operation.files_count} 个")
            lines.append(f"💿 文件大小: {operation.format_size(operation.total_size)}")
        
        if operation.actual_count > 0 or operation.status != 1:
            lines.append(f"✅ 传输文件: {operation.actual_count} 个")
        if operation.actual_size > 0 or operation.status != 1:
            lines.append(f"📊 传输大小: {operation.format_size(operation.actual_size)}")
        if operation.actual_time > 0 or operation.status != 1:
            lines.append(f"⏱️ 传输耗时: {operation.format_actual_time()}")
        
        if operation.error_code != 0 or operation.error_message:
            lines.append(f"❌ 错误代码: {operation.error_code}")
            if operation.error_message:
                lines.append(f"⚠️ 错误信息: {operation.error_message}")
        
        return "\n".join(lines)
    
    def process_operations(self, operations: List[BackupOperation]) -> bool:
        """
        处理并推送备份操作
        
        Args:
            operations: 备份操作列表
            
        Returns:
            是否推送成功
        """
        if not operations:
            return True
        
        try:
            # 检查是否在免打扰时间段
            if self.dnd_service and self.dnd_service.should_cache_now():
                logger.info(f"在免打扰时间段，缓存 {len(operations)} 条备份消息")
                # 格式化消息用于缓存
                if len(operations) == 1:
                    content = self.format_operation_message(operations[0])
                else:
                    content = f"💾 发现 {len(operations)} 条新的备份操作"
                self.dnd_service.cache_message(content)
                return True
            
            # 格式化消息
            if len(operations) == 1:
                content = self.format_operation_message(operations[0])
            else:
                content = f"💾 发现 {len(operations)} 条新的备份操作\n\n"
                for op in operations[:5]:  # 最多显示5条
                    task_info = self.backup_db_service.get_task_info(op.task_id) if self.backup_db_service else None
                    task_name = task_info.get('name', '未知') if task_info else '未知'
                    status_emoji = {1: "🚀", 2: "🔄", 3: "✅", 4: "❌", 5: "🚫", 0: "❓"}.get(op.status, "❓")
                    content += f"{status_emoji} {task_name}: {op.get_status_name()}\n"
                
                if len(operations) > 5:
                    content += f"\n... 还有 {len(operations) - 5} 条操作"
            
            # 推送
            enabled_channels = self.config.get('push_channels', {})
            success = self.push_service.push_message(content, enabled_channels)
            
            # 记录到推送历史
            from models.push_history import PushHistory
            from utils.time_utils import TimeUtils
            # 使用第一条备份操作的start_time作为last_id，便于追溯
            backup_start_time = operations[0].start_time if operations else 0
            
            # 构建预览消息：开始时间 + 任务名称 + 状态
            if len(operations) == 1:
                op = operations[0]
                task_info = self.backup_db_service.get_task_info(op.task_id) if self.backup_db_service else None
                task_name = task_info.get('name', '未知任务') if task_info else '未知任务'
                preview = f"{op.get_start_time_str()} {task_name} {op.get_status_name()}"
            else:
                preview = f"{len(operations)} 条备份操作"
            
            history = PushHistory(
                timestamp=TimeUtils.get_current_datetime_str(),
                content=content,
                preview=preview,
                success=success,
                count=len(operations),
                last_id=backup_start_time,  # 记录备份开始时间
                source='backup'  # 标记来源为备份
            )
            self.history_service.add_history(history)
            
            logger.info(f"推送了 {len(operations)} 条备份操作，成功: {success}")
            return success
            
        except Exception as e:
            logger.error(f"处理备份操作时出错: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取备份监控状态

        Returns:
            状态字典
        """
        # 查询备份库最新1条记录的 start_time（开始时间对所有操作都有值，更可靠）
        last_backup_time = None
        if self.backup_db_available and self.backup_db_service:
            try:
                with self.backup_db_service.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT start_time FROM operations "
                        "ORDER BY start_time DESC LIMIT 1"
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        last_backup_time = datetime.fromtimestamp(row[0]).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.warning(f"获取最后备份时间失败: {e}")

        return {
            "enabled": self.is_enabled(),
            "db_available": self.backup_db_available,
            "last_start_time": self.last_start_time,
            "running": self.running,
            "last_backup_time": last_backup_time,
            "last_finished_time": last_backup_time  # 兼容旧字段名
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取备份数据库统计信息
        
        Returns:
            统计信息字典
        """
        if not self.backup_db_available or not self.backup_db_service:
            return {
                "total_tasks": 0,
                "recent_operations_count": 0,
                "last_operation_time": None
            }
        
        try:
            with self.backup_db_service.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取备份任务总数（user_tasks表）
                cursor.execute("SELECT COUNT(*) FROM user_tasks")
                total_tasks = cursor.fetchone()[0]
                
                # 获取operations表总记录数
                cursor.execute("SELECT COUNT(*) FROM operations")
                total_operations = cursor.fetchone()[0]
                
                # 获取最近24小时的记录数（使用时间戳计算，假设start_time是秒级时间戳）
                cursor.execute("""
                    SELECT COUNT(*) FROM operations 
                    WHERE start_time >= ?
                """, (int(datetime.now().timestamp()) - 86400,))
                recent_operations_count = cursor.fetchone()[0]
                
                # 获取最新记录时间（时间戳）- 备份数据库时间戳为本地时间，直接格式化
                cursor.execute("SELECT MAX(start_time) FROM operations")
                last_operation_timestamp = cursor.fetchone()[0]
                
                # 备份数据库时间戳为本地时间，直接格式化为日期时间字符串
                if last_operation_timestamp:
                    last_operation_time = datetime.fromtimestamp(last_operation_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    last_operation_time = None
                
                return {
                    "total_tasks": total_tasks,
                    "total_operations": total_operations,
                    "recent_operations_count": recent_operations_count,
                    "last_operation_time": last_operation_time,
                    "last_backup_time": last_operation_time  # 统一字段名
                }
        except Exception as e:
            logger.error(f"获取备份数据库统计信息时出错: {e}")
            return {
                "total_tasks": 0,
                "total_operations": 0,
                "recent_operations_count": 0,
                "last_operation_time": None,
                "error": str(e)
            }
    
    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的备份操作记录
        
        Args:
            limit: 返回记录数量
            
        Returns:
            操作记录列表
        """
        if not self.backup_db_available or self.backup_db_service is None:
            return []
        
        operations = self.backup_db_service.get_recent_operations(limit)
        
        # 附加任务信息和时间转换
        result = []
        for op in operations:
            task_info = self.backup_db_service.get_task_info(op.get('task_id', 0))
            op['task_name'] = task_info.get('name', '未知') if task_info else '未知'
            op['status_name'] = OPERATION_STATUS_MAP.get(op.get('status', 0), '未知')
            
            # 转换时间戳为本地时间格式（备份数据库时间戳为本地时间）
            if op.get('start_time'):
                op['start_time_str'] = datetime.fromtimestamp(op['start_time']).strftime('%Y-%m-%d %H:%M:%S')
            if op.get('finished_time'):
                op['finished_time_str'] = datetime.fromtimestamp(op['finished_time']).strftime('%Y-%m-%d %H:%M:%S')
            
            result.append(op)
        
        return result
    
    def test_connection(self, db_path: str) -> Dict[str, Any]:
        """
        测试数据库连接
        
        Args:
            db_path: 数据库路径
            
        Returns:
            测试结果
        """
        try:
            if not os.path.exists(db_path):
                return {
                    "success": False,
                    "message": f"数据库文件不存在: {db_path}"
                }
            
            test_service = BackupDatabaseService(db_path)
            if test_service.check_connection():
                max_id = test_service.get_max_operation_id()
                return {
                    "success": True,
                    "message": f"连接成功，当前最大操作ID: {max_id}",
                    "max_id": max_id
                }
            else:
                return {
                    "success": False,
                    "message": "数据库连接失败"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}"
            }
