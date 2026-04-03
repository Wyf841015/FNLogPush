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

    return app
