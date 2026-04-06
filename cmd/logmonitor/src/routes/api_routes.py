#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用API路由模块
处理健康检查等通用API
"""
import logging
import os
import platform
import sys

import psutil
from flask import Flask, jsonify

from utils import api_error_handler

logger = logging.getLogger(__name__)


def get_health_data() -> dict:
    """
    获取系统健康数据（供WebSocket推送使用）
    
    Returns:
        dict: 健康数据字典
    """
    try:
        # 获取CPU信息
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "cpu_percent": psutil.cpu_percent(interval=0),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
        }

        # 获取内存信息
        memory_info = psutil.virtual_memory()._asdict()

        # 获取进程信息
        process_info = {
            "pid": os.getpid(),
            "name": psutil.Process(os.getpid()).name(),
            "memory_percent": psutil.Process(os.getpid()).memory_percent(),
            "cpu_percent": psutil.Process(os.getpid()).cpu_percent(interval=0)
        }

        # 获取数据库健康信息
        db_health = {"status": "not_initialized"}
        try:
            from monitor_core import get_monitor
            monitor = get_monitor()
            if monitor and monitor.db_service:
                db_health = monitor.db_service.health_check()
        except Exception as db_err:
            logger.debug(f"获取数据库健康状态失败: {db_err}")
            db_health = {"status": "error", "error": str(db_err)}

        return {
            "status": "healthy",
            "timestamp": int(__import__('time').time()),
            "cpu": cpu_info,
            "memory": memory_info,
            "process": process_info,
            "database": db_health
        }
    except ImportError:
        return {
            "status": "healthy",
            "message": "psutil not installed, basic health check only"
        }
    except Exception as e:
        logger.error(f"获取健康数据失败: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def register_api_routes(app: Flask):
    """
    注册通用API路由

    Args:
        app: Flask应用实例
    """

    @app.route('/api/health', methods=['GET'])
    @api_error_handler
    def health_check():
        """系统健康检查"""
        try:
            # 获取系统信息
            system_info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python_version": platform.python_version()
            }

            # 获取CPU信息
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "cpu_percent": psutil.cpu_percent(interval=0),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
            }

            # 获取内存信息
            memory_info = psutil.virtual_memory()._asdict()

            # 获取磁盘信息
            disk_info = {}
            if sys.platform == 'win32':
                disk_usage = psutil.disk_usage('C:')
                disk_info = {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": disk_usage.percent
                }
            else:
                for partition in psutil.disk_partitions():
                    if partition.mountpoint == '/':
                        disk_usage = psutil.disk_usage(partition.mountpoint)
                        disk_info = {
                            "total": disk_usage.total,
                            "used": disk_usage.used,
                            "free": disk_usage.free,
                            "percent": disk_usage.percent
                        }
                        break

            # 获取进程信息
            process_info = {
                "pid": os.getpid(),
                "name": psutil.Process(os.getpid()).name(),
                "memory_percent": psutil.Process(os.getpid()).memory_percent(),
                "cpu_percent": psutil.Process(os.getpid()).cpu_percent(interval=0)
            }

            # 获取网络信息
            network_info = {"interfaces": {}}
            for interface, addrs in psutil.net_if_addrs().items():
                network_info["interfaces"][interface] = [addr.address for addr in addrs]

            # 获取数据库健康信息
            db_health = {"status": "not_initialized"}
            try:
                from monitor_core import get_monitor
                monitor = get_monitor()
                if monitor and monitor.db_service:
                    db_health = monitor.db_service.health_check()
            except Exception as db_err:
                logger.warning(f"获取数据库健康状态失败: {db_err}")
                db_health = {"status": "error", "error": str(db_err)}

            return jsonify({
                "status": "healthy",
                "system": system_info,
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "process": process_info,
                "network": network_info,
                "database": db_health
            })
        except ImportError:
            return jsonify({
                "status": "healthy",
                "message": "psutil not installed, basic health check only"
            })
        except Exception as e:
            logger.error(f"健康检查失败: {e}", exc_info=True)
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            })

    @app.route('/api/push/stats', methods=['GET'])
    @api_error_handler
    def push_stats():
        """推送服务统计信息（队列、重试堆、成功/失败/死信计数）"""
        try:
            from monitor_core import get_monitor
            monitor = get_monitor()
            if not monitor or not hasattr(monitor, 'push_service'):
                return jsonify({"error": "推送服务未启动"}), 503
            return jsonify(monitor.push_service.get_stats())
        except Exception as e:
            logger.error(f"获取推送统计失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/push/dead-letters', methods=['GET'])
    @api_error_handler
    def push_dead_letters():
        """查询死信区列表（最近 200 条）"""
        try:
            from monitor_core import get_monitor
            monitor = get_monitor()
            if not monitor or not hasattr(monitor, 'push_service'):
                return jsonify({"error": "推送服务未启动"}), 503
            items = monitor.push_service.get_dead_letters()
            return jsonify({"total": len(items), "items": items})
        except Exception as e:
            logger.error(f"查询死信区失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/push/dead-letters/<int:dlq_id>/requeue', methods=['POST'])
    @api_error_handler
    def requeue_dead_letter(dlq_id: int):
        """将死信区指定记录重新投入推送队列"""
        try:
            from monitor_core import get_monitor
            monitor = get_monitor()
            if not monitor or not hasattr(monitor, 'push_service'):
                return jsonify({"error": "推送服务未启动"}), 503
            success = monitor.push_service.requeue_dead_letter(dlq_id)
            if success:
                return jsonify({"success": True, "message": f"死信记录 {dlq_id} 已重新入队"})
            else:
                return jsonify({"success": False, "message": f"重新入队失败，记录 {dlq_id} 不存在或队列已满"}), 400
        except Exception as e:
            logger.error(f"死信重发失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/alert-aggregation/stats', methods=['GET'])
    @api_error_handler
    def alert_aggregation_stats():
        """
        告警聚合统计：返回总接收/推送/压制/静默次数及当前参数配置。
        """
        try:
            from monitor_core import get_monitor
            monitor = get_monitor()
            if not monitor or not hasattr(monitor, 'alert_aggregator'):
                return jsonify({"error": "告警聚合器未初始化"}), 503
            return jsonify(monitor.alert_aggregator.get_stats())
        except Exception as e:
            logger.error(f"获取告警聚合统计失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/alert-aggregation/groups', methods=['GET'])
    @api_error_handler
    def alert_aggregation_groups():
        """
        当前活跃聚合组列表：显示每个 (eventId, serviceId, loglevel) 组合
        的计数、压制数、剩余窗口时间及是否静默。
        """
        try:
            from monitor_core import get_monitor
            monitor = get_monitor()
            if not monitor or not hasattr(monitor, 'alert_aggregator'):
                return jsonify({"error": "告警聚合器未初始化"}), 503
            groups = monitor.alert_aggregator.get_active_groups()
            return jsonify({"total": len(groups), "groups": groups})
        except Exception as e:
            logger.error(f"获取活跃聚合组失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    def _find_events_json():
        """查找 events.json 文件的多个可能位置（与 config.json 逻辑一致）"""
        import os
        from pathlib import Path
        
        # APP_HOME 目录（与 app.py 中一致）
        app_home = os.environ.get('APP_HOME')
        
        # 可能的路径（按优先级排序）
        possible_paths = []
        
        # 1. APP_HOME/config/events.json（优先，与 config.json 逻辑一致）
        if app_home:
            possible_paths.append(Path(app_home) / 'config' / 'events.json')
        
        # 2. 源码目录下的 events.json
        possible_paths.append(Path(__file__).parent / 'events.json')           # routes/events.json
        possible_paths.append(Path(__file__).parent.parent / 'events.json')    # src/events.json
        possible_paths.append(Path(__file__).parent.parent / 'config' / 'events.json')  # src/config/events.json
        
        for path in possible_paths:
            if path.exists():
                return path
        return None

    @app.route('/api/events/config', methods=['GET'])
    @api_error_handler
    def events_config():
        """
        获取事件配置（从 events.json 文件加载）
        """
        try:
            import json
            from pathlib import Path
            
            # 获取事件配置文件路径（搜索多个可能位置）
            events_file = _find_events_json()
            
            if events_file:
                with open(events_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return jsonify({
                    "status": "success",
                    "source": str(events_file),
                    "config": config
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "事件配置文件不存在"
                }), 404
        except Exception as e:
            logger.error(f"加载事件配置失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/events/mappings', methods=['GET'])
    @api_error_handler
    def events_mappings():
        """
        获取事件映射（从 mappings.py 内置映射 + events.json 配置合并）
        """
        try:
            from config.mappings import EventMappings
            
            mappings = EventMappings()
            # 获取所有内置映射
            all_events = {}
            for event_id, event_name in EventMappings.EVENT_NAME_MAP.items():
                all_events[event_id] = {
                    "name": event_name,
                    "source": "builtin"
                }
            
            # 尝试合并 events.json 配置
            try:
                events_file = _find_events_json()
                if events_file:
                    import json
                    with open(events_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    for category in config.get('categories', []):
                        for event in category.get('events', []):
                            event_id = event.get('id')
                            if event_id:
                                all_events[event_id] = {
                                    "name": event.get('name', event_id),
                                    "source": "config"
                                }
            except Exception as config_err:
                logger.debug(f"合并事件配置失败: {config_err}")
            
            return jsonify({
                "status": "success",
                "total": len(all_events),
                "mappings": all_events
            })
        except Exception as e:
            logger.error(f"获取事件映射失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return app
