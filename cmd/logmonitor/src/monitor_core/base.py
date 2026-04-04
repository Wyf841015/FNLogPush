#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志监控核心基础模块
包含主要的监控逻辑和类定义
"""
import time
import threading
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from config.manager import ConfigManager
from config.mappings import EventMappings
from services.database_service import DatabaseService
from services.push_service import PushService
from services.history_service import HistoryService
from services.dnd_service import DoNotDisturbService
from services.backup_monitor_service import BackupMonitorService
from models.log_record import LogRecord
from models.push_history import PushHistory
from utils.message_formatter import MessageFormatter
from utils.time_utils import TimeUtils
from utils.error_handler import LogMonitorError, DatabaseError, ConfigError, PushError
from websocket_manager import get_websocket_manager

from .dnd import DNDHandler
from .backup import BackupMonitorHandler
from .push_coordinator import PushCoordinator
from .alert_aggregator import AlertAggregator

logger = logging.getLogger(__name__)


class LogMonitor:
    """日志监控核心类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化日志监控

        Args:
            config_path: 配置文件路径，默认为APP_HOME/config/config.json
        """
        # 如果没有传入config_path，使用APP_HOME环境变量
        if config_path is None:
            app_home = os.environ.get('APP_HOME', '')
            if app_home:
                config_path = os.path.join(app_home, 'config', 'config.json')
            else:
                config_path = 'config.json'
        
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config

        # 配置锁，防止并发更新
        self._config_lock = threading.RLock()

        # 初始化数据库服务
        self.db_path = self.config['database_path']
        self.db_service = None
        self.db_available = False

        # 检查数据库是否存在,不存在则标记为不可用
        if os.path.exists(self.db_path):
            self.db_service = DatabaseService(self.db_path)
            self.db_available = True
            logger.info(f"数据库已连接: {self.db_path}")
            # 创建数据库索引以提高查询性能
            self.db_service.create_indexes()
        else:
            logger.warning(f"数据库文件不存在: {self.db_path}")
            logger.warning("监控功能暂不可用,请通过Web界面配置数据库路径")

        # 初始化推送服务
        self.push_service = PushService()
        self.push_service.configure_from_config(self.config)

        # 初始化历史记录服务
        self.history_service = HistoryService(
            history_file='push_history.json',
            max_size=self.config['history_size']
        )

        # 初始化免打扰服务
        self.dnd_service = DoNotDisturbService(self.config.get('do_not_disturb', {}))

        # 初始化备份监控服务
        self.backup_monitor = BackupMonitorService(
            self.config,
            self.push_service,
            self.history_service,
            self.dnd_service
        )

        # 初始化工具类（保留供 status/preview 等少量地方使用）
        self.mappings = EventMappings()
        self.formatter = MessageFormatter()
        self.time_utils = TimeUtils()

        # 初始化推送协调器（封装 DND 判断 + 推送 + 历史记录）
        self.push_coordinator = PushCoordinator(
            push_service=self.push_service,
            history_service=self.history_service,
            dnd_service=self.dnd_service,
            config=self.config,
            formatter=self.formatter,
            time_utils=self.time_utils,
            mappings=self.mappings,
        )

        # 监控状态
        self.last_id = 0
        self.running = False
        self.thread = None
        self.last_history_index = 0  # 用于跟踪历史记录变化
        self.last_push_results = None  # 上次推送结果

        # 初始化处理器
        self.dnd_handler = DNDHandler(self.dnd_service)
        self.backup_handler = BackupMonitorHandler(self.backup_monitor)

        # 初始化告警聚合与降噪器
        _agg_cfg = self.config.get('alert_aggregation', {})
        self.alert_aggregator = AlertAggregator(
            window_seconds=_agg_cfg.get('window_seconds', 300),
            threshold=_agg_cfg.get('threshold', 5),
            silence_seconds=_agg_cfg.get('silence_seconds', 600),
            enabled=_agg_cfg.get('enabled', True),
        )

        # 初始化最后ID
        self.init_last_id()

        # 初始化历史记录索引
        self.last_history_index = self.history_service.get_count()

        logger.info("日志监控核心初始化完成")
    
    def init_last_id(self):
        """初始化最后处理的ID"""
        try:
            # 如果数据库不可用，直接返回0
            if not self.db_available or self.db_service is None:
                logger.info("数据库不可用，设置初始ID为0")
                self.last_id = 0
                return

            # 直接从数据库获取最大ID作为初始last_id
            # 这样可以确保系统启动后只推送新的日志记录
            last_id = self.db_service.get_max_id()
            logger.info(f"从数据库获取最大ID: {last_id}")

            self.last_id = last_id
            logger.info(f"初始化最后ID完成: {self.last_id}")
        except DatabaseError as e:
            logger.error(f"数据库错误: {e.message}")
            self.last_id = 0
        except Exception as e:
            logger.error(f"初始化最后ID时出错: {e}")
            logger.exception(e)  # 记录完整的异常堆栈
            self.last_id = 0
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        更新配置（线程安全）

        Args:
            new_config: 新的配置项

        Returns:
            是否更新成功
        """
        with self._config_lock:  # 加锁保护配置更新
            try:
                logger.info(f"开始更新配置: {list(new_config.keys())}")

                # 检查是否更新了数据库路径
                old_db_path = self.db_path
                new_db_path = new_config.get('database_path', old_db_path)

                # 更新配置管理器
                success = self.config_manager.update_config(new_config)
                if not success:
                    return False

                self.config = self.config_manager.config

                # 如果数据库路径变更,重新初始化数据库服务
                if 'database_path' in new_config and new_db_path != old_db_path:
                    logger.info(f"数据库路径变更: {old_db_path} -> {new_db_path}")
                    self.db_path = new_db_path

                    # 先关闭旧连接
                    if self.db_service:
                        self.db_service.connection_pool.close_all_connections()

                    if os.path.exists(new_db_path):
                        self.db_service = DatabaseService(new_db_path)
                        self.db_available = True
                        self.last_id = 0
                        self.init_last_id()
                        logger.info(f"数据库重新连接成功: {new_db_path}")

                        # 如果监控未运行，自动启动
                        if not self.running:
                            logger.info("监控未运行，自动启动监控")
                            self.start()
                            if self.running:
                                logger.info("✓ 数据库配置成功，监控已自动启动")
                            else:
                                logger.warning("监控启动失败")
                    else:
                        self.db_service = None
                        self.db_available = False
                        self.last_id = 0
                        logger.warning(f"数据库文件不存在: {new_db_path}")
                        logger.warning("监控功能暂不可用,请检查数据库路径")

                # 更新推送服务配置
                if any(key in new_config for key in ['webhook_url', 'wecom', 'push_channels', 'meow', 'dingtalk', 'feishu', 'bark', 'pushplus']):
                    self.push_service.configure_from_config(self.config)

                # 更新免打扰服务配置
                if 'do_not_disturb' in new_config:
                    self.dnd_service.update_config(self.config.get('do_not_disturb', {}))

                # 更新历史记录服务配置
                if 'history_size' in new_config:
                    self.history_service.max_size = self.config['history_size']

                # 更新备份监控服务配置
                if 'backup_monitor' in new_config:
                    self.backup_monitor.update_config(self.config, self.dnd_service)

                # 更新告警聚合配置
                if 'alert_aggregation' in new_config:
                    _agg = self.config.get('alert_aggregation', {})
                    self.alert_aggregator.update_config(
                        window_seconds=_agg.get('window_seconds'),
                        threshold=_agg.get('threshold'),
                        silence_seconds=_agg.get('silence_seconds'),
                        enabled=_agg.get('enabled'),
                    )

                logger.info("配置更新成功")
                return True
            except Exception as e:
                logger.error(f"更新配置时出错: {e}")
                return False
    
    def check_new_logs(self) -> int:
        """
        检查新的日志记录

        Returns:
            新日志数量
        """
        # 检查数据库是否可用
        if not self.db_available or self.db_service is None:
            return 0

        new_logs = []  # 提前初始化，避免作用域问题

        # DEBUG: 记录检查开始时的状态
        logger.debug(f"[DEBUG] check_new_logs: last_id={self.last_id}, running={self.running}")

        try:
            # 构建过滤条件（使用预构建的反向映射优化性能）
            level_codes = [
                self.mappings.LEVEL_NAME_TO_CODE[level_name]
                for level_name in self.config.get('selected_levels', [])
                if level_name in self.mappings.LEVEL_NAME_TO_CODE
            ]

            excluded_events = self.config.get('selected_events', [])

            # 查询新记录
            rows = self.db_service.get_logs_by_filter(
                self.last_id,
                level_codes,
                excluded_events
            )

            # 注意：即使没有新日志，也要检查备份操作
            # if not rows:
            #     return 0

            max_id = self.last_id

            for row in rows:
                log = LogRecord.from_dict(row)
                new_logs.append(log)
                if log.id > max_id:
                    max_id = log.id

            # 处理新日志
            if new_logs:
                logger.info(f"[DEBUG] 发现 {len(new_logs)} 条新日志，准备处理，IDs: {[log.id for log in new_logs]}")
                self.process_logs(new_logs)
                
                # 广播新日志事件到WebSocket客户端
                try:
                    ws_manager = get_websocket_manager()
                    ws_manager.broadcast('new_logs', {
                        'count': len(new_logs),
                        'ids': [log.id for log in new_logs],
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"WebSocket广播失败: {e}")

            # 定期清理到期聚合窗口并补发聚合摘要
            for agg_result in self.alert_aggregator.flush_expired():
                self._push_aggregated(agg_result)

            # 更新最后处理的ID
            if max_id > self.last_id:
                self.last_id = max_id
                logger.debug(f"更新最后ID: {self.last_id}")

            # 检查是否需要推送免打扰缓存的消息
            self.dnd_handler.check_dnd_cache(
                self.formatter, self.push_service, self.history_service,
                self.last_id, push_coordinator=self.push_coordinator
            )

        except DatabaseError as e:
            logger.error(f"数据库错误，检查日志失败: {e.message}")
            raise
        except Exception as e:
            logger.error(f"检查日志时出错: {e}", exc_info=True)

        # 始终检查备份操作（不依赖于是否有新日志）
        try:
            self.backup_handler.check_backup_operations()
        except Exception as e:
            logger.error(f"检查备份操作时出错: {e}", exc_info=True)

        return len(new_logs) if new_logs else 0
    
    def process_logs(self, logs: List[LogRecord]):
        """
        处理并推送日志

        Args:
            logs: 日志记录列表
        """
        if not logs:
            return

        logger.debug(f"[DEBUG] process_logs: 收到 {len(logs)} 条日志")

        # ── 告警聚合与降噪过滤 ────────────────────────────────────────
        # 每条日志先经过 AlertAggregator.feed()：
        #   - 返回 FeedResult → 立即推送（首条或聚合摘要）
        #   - 返回 None       → 被聚合/静默压制，跳过
        pass_through: List[LogRecord] = []
        for log in logs:
            result = self.alert_aggregator.feed(log)
            if result is not None:
                pass_through.append(log)

        if not pass_through:
            logger.debug(f"[DEBUG] process_logs: 所有日志被聚合/压制，不推送")
            return

        logger.info(f"[DEBUG] process_logs: {len(pass_through)} 条日志需要推送")
        # 直接推送通过聚合器的日志
        self._push_logs(pass_through)
    
    def _push_logs(self, logs: List[LogRecord]):
        """
        推送日志（委托给 PushCoordinator，含 DND 判断 → 推送 → 历史记录）

        Args:
            logs: 日志记录列表
        """
        if not logs:
            return
        logger.info(f"[DEBUG] _push_logs: 准备推送 {len(logs)} 条日志，IDs: {[log.id for log in logs]}")
        self.push_coordinator.push(logs, last_id=self.last_id)

    def _push_aggregated(self, agg_result: "AlertAggregator.FeedResult"):
        """
        推送聚合摘要（窗口到期后补发）

        消息在原格式基础上加上「[聚合 N 次]」前缀，让运维感知到
        窗口内被压制的告警数量。

        Args:
            agg_result: AlertAggregator.flush_expired() 返回的 FeedResult
        """
        if not agg_result or not agg_result.logs:
            return
        try:
            # 格式化基础消息
            logs = agg_result.logs
            base_content = (
                self.formatter.format_single_log(logs[0])
                if len(logs) == 1
                else self.formatter.format_batch_logs(logs)
            )
            # 在最前面追加聚合摘要标注
            agg_header = (
                f"[聚合告警] 共触发 {agg_result.count} 次"
                f"（含 {agg_result.suppressed} 次被压制）\n"
            )
            content = agg_header + base_content

            enabled_channels = self.config.get('push_channels', {})
            self.push_coordinator.push_raw(
                content=content,
                logs=logs,
                last_id=self.last_id,
                enabled_channels=enabled_channels,
            )
            logger.info(
                f"[聚合] 发送聚合摘要: key={agg_result.key}, "
                f"total={agg_result.count}, suppressed={agg_result.suppressed}"
            )
        except Exception as e:
            logger.error(f"推送聚合摘要时出错: {e}", exc_info=True)
    
    def _build_preview(self, logs: List[LogRecord]) -> str:
        """构建预览信息（委托给 PushCoordinator）"""
        return self.push_coordinator.build_preview(logs)
    
    def start(self):
        """启动监控"""
        if self.running:
            logger.warning("监控已经在运行中")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.thread.start()
        logger.info("日志监控已启动")
        if not self.db_available:
            logger.warning("数据库当前不可用，监控将持续等待数据库就绪后自动开始")
        logger.info("✓ 系统已就绪，开始监控FNOS日志哨兵系统")
    
    def stop(self):
        """停止监控"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("日志监控已停止")
    
    def _run_monitor(self):
        """
        监控主循环
        check_interval 在每次循环结束时动态读取，支持配置热更新。
        """
        logger.info(f"监控循环启动，检查间隔: {self.config.get('check_interval', 5)} 秒")
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self.running:
            try:
                count = self.check_new_logs()
                if count > 0:
                    logger.info(f"发现 {count} 条新日志")

                # 重置连续错误计数
                consecutive_errors = 0

            except DatabaseError as e:
                consecutive_errors += 1
                logger.error(f"数据库错误: {e.message}")
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"连续{consecutive_errors}次数据库错误，监控循环将短暂暂停后重试")
                    time.sleep(30)  # 暂停30秒后重试
                    consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"监控循环出错: {e}", exc_info=True)
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"连续{consecutive_errors}次严重错误，监控循环将短暂暂停后重试")
                    time.sleep(30)
                    consecutive_errors = 0

            # 每次循环结束时重新读取间隔，支持配置热更新
            check_interval = self.config.get('check_interval', 5)
            time.sleep(check_interval)

        logger.info("监控循环已退出")
    
    def restart(self, new_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        重启监控
        
        Args:
            new_config: 新的配置(可选)
            
        Returns:
            是否重启成功
        """
        try:
            self.stop()
            time.sleep(1)
            
            if new_config:
                self.update_config(new_config)
                self.init_last_id()
            
            self.start()
            return True
        except Exception as e:
            logger.error(f"重启监控时出错: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态

        Returns:
            状态字典
        """
        current_history_count = self.history_service.get_count()
        # 更新历史记录索引
        self.last_history_index = current_history_count

        # 检查数据库连接状态
        db_connection_status = self._check_database_connection()

        # 获取备份监控状态
        backup_status = self.backup_monitor.get_status() if self.backup_monitor else {}

        return {
            "running": self.running,
            "last_id": self.last_id,
            "config": self.config,
            "history_count": current_history_count,
            "last_history_index": self.last_history_index,
            "last_history_timestamp": self.history_service.get_last_timestamp(),
            "dnd_enabled": self.dnd_service.is_enabled(),
            "dnd_cache_count": self.dnd_service.get_cache_count(),
            "db_available": self.db_available,
            "db_connection_status": db_connection_status,
            "backup_monitor": backup_status,
            "alert_aggregation": self.alert_aggregator.get_stats(),
        }
    
    def _check_database_connection(self) -> str:
        """
        检查数据库连接状态（不发 SQL，直接读连接池内存状态，避免占用连接）

        Returns:
            连接状态: "已连接"、"未连接" 或 "连接失败"
        """
        if not self.db_available or self.db_service is None:
            return "未连接"

        try:
            pool_status = self.db_service.connection_pool.get_pool_status()
            # 连接池已初始化且有连接（可用或正在使用）即视为已连接
            if pool_status.get("initialized") and (
                pool_status.get("available", 0) > 0 or pool_status.get("in_use", 0) > 0
            ):
                return "已连接"
            return "连接失败"
        except Exception as e:
            logger.error(f"检查数据库连接时出错: {e}")
            return "连接失败"
    
    def get_history(self, limit: int = 20, offset: int = 0, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        获取推送历史，支持分页和日期筛选

        Args:
            limit: 返回数量限制
            offset: 偏移量（用于分页）
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)

        Returns:
            包含历史记录和总数信息的字典
        """
        histories = self.history_service.get_recent_history(limit, offset, start_date, end_date)
        total = self.history_service.get_count(start_date, end_date)
        return {
            'data': [h.to_dict() for h in histories],
            'total': total,
            'offset': offset,
            'limit': limit
        }
    
    def get_history_detail(self, history_id: int) -> Dict[str, Any]:
        """
        获取历史记录详情
        
        Args:
            history_id: 历史记录索引
            
        Returns:
            历史记录详情
        """
        history = self.history_service.get_history_by_id(history_id)
        if history:
            return {'success': True, 'data': history.to_dict()}
        return {'success': False, 'message': '历史记录不存在'}
    
    def push_message(self, content: str) -> bool:
        """
        推送测试消息
        
        Args:
            content: 消息内容
            
        Returns:
            是否推送成功
        """
        enabled_channels = self.config.get('push_channels', {})
        channel_results = self.push_service.push_message(content, enabled_channels)
        # 保存结果供历史记录使用
        self.last_push_results = channel_results
        # 返回是否有至少一个渠道成功
        return bool(channel_results) and any(channel_results.values())
    
    def get_backup_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的备份操作记录
        
        Args:
            limit: 返回记录数量
            
        Returns:
            操作记录列表
        """
        if self.backup_monitor:
            return self.backup_monitor.get_recent_operations(limit)
        return []
    
    def test_backup_db(self, db_path: str) -> Dict[str, Any]:
        """
        测试备份数据库连接
        
        Args:
            db_path: 数据库路径
            
        Returns:
            测试结果
        """
        if self.backup_monitor:
            return self.backup_monitor.test_connection(db_path)
        return {"success": False, "message": "备份监控服务未初始化"}


# 全局监控实例
_monitor_instance: Optional[LogMonitor] = None


def get_monitor() -> Optional[LogMonitor]:
    """
    获取或创建监控实例
    
    Returns:
        监控实例
    """
    global _monitor_instance
    if _monitor_instance is None:
        try:
            # 使用APP_HOME环境变量构建config_path
            app_home = os.environ.get('APP_HOME', '')
            if app_home:
                config_path = os.path.join(app_home, 'config', 'config.json')
            else:
                config_path = 'config.json'
            _monitor_instance = LogMonitor(config_path)
        except Exception as e:
            logger.error(f"创建监控实例失败: {e}")
            return None
    return _monitor_instance
