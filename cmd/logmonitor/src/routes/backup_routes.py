#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份监控相关路由模块
处理备份数据库的监控API
"""
from flask import Flask, request, jsonify, session
import logging

from monitor_core import get_monitor
from utils import api_error_handler
from utils.auth import login_required  # 统一出口

logger = logging.getLogger(__name__)


def register_backup_routes(app: Flask):
    """
    注册备份监控相关路由

    Args:
        app: Flask应用实例
    """

    @app.route('/api/backup/operations', methods=['GET'])
    @login_required
    @api_error_handler
    def get_backup_operations():
        """获取最近的备份操作记录"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        limit = request.args.get('limit', 10, type=int)
        operations = monitor.get_backup_operations(limit)
        return jsonify(operations)

    @app.route('/api/backup/test-connection', methods=['POST'])
    @login_required
    @api_error_handler
    def test_backup_db_connection():
        """测试备份数据库连接"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"success": False, "error": "监控程序未启动"}), 500

        data = request.json
        db_path = data.get('database_path')

        if not db_path:
            return jsonify({"success": False, "error": "缺少数据库路径参数"})

        result = monitor.test_backup_db(db_path)
        return jsonify(result)

    @app.route('/api/backup/status', methods=['GET'])
    @login_required
    @api_error_handler
    def get_backup_status():
        """获取备份监控状态"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        if monitor.backup_monitor:
            return jsonify(monitor.backup_monitor.get_status())
        return jsonify({
            "enabled": False,
            "db_available": False,
            "last_start_time": 0,
            "running": False
        })

    @app.route('/api/backup/statistics', methods=['GET'])
    @login_required
    @api_error_handler
    def get_backup_statistics():
        """获取备份数据库统计信息"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        if monitor.backup_monitor:
            return jsonify(monitor.backup_monitor.get_statistics())
        return jsonify({
            "total_tasks": 0,
            "total_operations": 0,
            "recent_operations_count": 0,
            "last_operation_time": None
        })

    return app
