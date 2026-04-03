#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控相关路由模块
处理监控状态、配置、控制等API
"""
from flask import Flask, request, jsonify, session
import logging

from monitor_core import get_monitor
from utils import api_error_handler
from utils.auth import login_required  # 统一出口，不再各自定义

logger = logging.getLogger(__name__)

# 敏感字段列表，GET /api/config 返回时自动脱敏
# webhook_url 是普通 URL，不做脱敏，用户需要能看到和修改当前配置的地址
_SENSITIVE_CONFIG_KEYS = {'password_hash', 'secret', 'token'}


def _sanitize_config(config: dict) -> dict:
    """
    递归脱敏配置字典，将敏感键值替换为 '***'。
    """
    sanitized = {}
    for k, v in config.items():
        if k.lower() in _SENSITIVE_CONFIG_KEYS or any(s in k.lower() for s in ('secret', 'token', 'password')):
            sanitized[k] = '***'
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_config(v)
        else:
            sanitized[k] = v
    return sanitized


def register_monitor_routes(app: Flask):
    """
    注册监控相关路由

    Args:
        app: Flask应用实例
    """

    @app.route('/api/status')
    @login_required
    @api_error_handler
    def get_status():
        """获取监控状态"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        status = monitor.get_status()

        if hasattr(monitor, 'db_available'):
            status['db_available'] = monitor.db_available
            if not monitor.db_available:
                status['db_message'] = "数据库文件不存在,请配置正确的数据库路径"
            else:
                status['db_message'] = "数据库连接正常"

        return jsonify(status)

    @app.route('/api/config', methods=['GET', 'POST'])
    @login_required
    @api_error_handler
    def config():
        """获取或更新配置"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        if request.method == 'POST':
            new_config = request.json
            logger.info(f"收到配置更新请求: {list(new_config.keys()) if new_config else 'None'}")

            try:
                success = monitor.update_config(new_config)

                response = {"success": success}
                if success and 'database_path' in new_config:
                    response['monitor_running'] = monitor.running
                    response['db_available'] = monitor.db_available
                    if monitor.db_available and monitor.running:
                        response['message'] = '数据库配置成功，监控已自动启动'
                    elif monitor.db_available and not monitor.running:
                        response['message'] = '数据库配置成功，请手动启动监控'
                    else:
                        response['message'] = '数据库路径无效，请检查配置'

                return jsonify(response)
            except Exception as e:
                logger.error(f"更新配置时发生异常: {e}", exc_info=True)
                return jsonify({"success": False, "error": str(e)})
        else:
            return jsonify(_sanitize_config(monitor.config))

    @app.route('/api/history')
    @login_required
    @api_error_handler
    def history():
        """获取推送历史，支持分页和日期筛选"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        history_data = monitor.get_history(limit, offset, start_date, end_date)
        return jsonify(history_data)

    @app.route('/api/history/<int:history_id>')
    @api_error_handler
    def history_detail(history_id):
        """获取单条历史记录详情"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({'success': False, 'message': '监控服务未启动'})

        try:
            result = monitor.get_history_detail(history_id)
            return jsonify(result)
        except Exception as e:
            logger.error(f"获取历史记录详情失败: {e}")
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/api/control', methods=['POST'])
    @login_required
    @api_error_handler
    def control():
        """控制监控程序"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        action = request.json.get('action')

        if action == 'start':
            monitor.start()
        elif action == 'stop':
            monitor.stop()
        elif action == 'restart':
            monitor.restart()
        elif action == 'reset_id':
            if not hasattr(monitor, 'db_available') or not monitor.db_available or monitor.db_service is None:
                return jsonify({"success": False, "error": "数据库不可用，无法获取最大ID"})

            max_id = monitor.db_service.get_max_id()
            monitor.last_id = max_id
            return jsonify({
                "success": True,
                "message": f"最后ID已设置为当前数据库最大ID: {max_id}",
                "new_id": max_id
            })
        elif action == 'reset_monitor':
            """重置监控：从数据库重新读取最后日志ID和最后备份时间"""
            # 重置日志监控的最后ID
            if not hasattr(monitor, 'db_available') or not monitor.db_available or monitor.db_service is None:
                return jsonify({"success": False, "error": "数据库不可用，无法获取最大ID"})

            max_id = monitor.db_service.get_max_id()
            monitor.last_id = max_id

            # 重置备份监控的最后时间
            reset_backup = False
            backup_time = 0
            if hasattr(monitor, 'backup_monitor') and monitor.backup_monitor:
                if hasattr(monitor.backup_monitor, 'backup_db_service') and monitor.backup_monitor.backup_db_service:
                    backup_time = monitor.backup_monitor.backup_db_service.get_max_start_time()
                    monitor.backup_monitor.last_start_time = backup_time
                    reset_backup = True

            message_parts = [f"最后日志ID已设置为当前数据库最大ID: {max_id}"]
            if reset_backup:
                message_parts.append(f"最后备份时间已设置为当前数据库最大时间: {backup_time}")

            return jsonify({
                "success": True,
                "message": "、".join(message_parts),
                "new_id": max_id,
                "new_backup_time": backup_time if reset_backup else None
            })
        else:
            return jsonify({"error": "未知操作"}), 400

        return jsonify({"success": True})

    @app.route('/api/test-webhook', methods=['POST'])
    @api_error_handler
    def test_webhook():
        """测试Webhook"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        test_message = "测试消息 - 这是来自Web界面的测试推送"
        success = monitor.push_message(test_message)

        return jsonify({"success": success})

    @app.route('/api/check-db', methods=['GET'])
    @api_error_handler
    def check_db():
        """检查数据库状态"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"error": "监控程序未启动"}), 500

        if not hasattr(monitor, 'db_available') or not monitor.db_available or monitor.db_service is None:
            return jsonify({
                "success": False,
                "error": "数据库文件不存在或无法访问",
                "message": "请检查配置中的数据库路径是否正确",
                "db_path": monitor.db_path if hasattr(monitor, 'db_path') else "未知"
            })

        try:
            columns = monitor.db_service.get_table_info()
            total_records = monitor.db_service.get_total_count()
            recent_records = monitor.db_service.get_recent_logs(5)
            event_stats = monitor.db_service.get_event_id_statistics()
            all_event_ids = monitor.db_service.get_event_id_list()
            known_event_ids = monitor.config.get('event_ids', [])
            new_event_ids = monitor.db_service.get_new_event_ids(known_event_ids)

            return jsonify({
                "success": True,
                "table_exists": True,
                "columns": columns or [],
                "total_records": total_records,
                "recent_records_count": len(recent_records),
                "monitor_last_id": monitor.last_id,
                "db_path": monitor.db_path,
                "event_statistics": event_stats,
                "total_event_types": len(event_stats),
                "new_event_ids": new_event_ids,
                "new_event_count": len(new_event_ids),
                "total_known_events": len(known_event_ids),
                "total_events_in_db": len(all_event_ids)
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            })

    @app.route('/api/test-db-connection', methods=['POST'])
    @api_error_handler
    def test_db_connection():
        """测试数据库连接"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"success": False, "error": "监控程序未启动"}), 500

        data = request.json
        db_path = data.get('database_path')

        if not db_path:
            return jsonify({"success": False, "error": "缺少数据库路径参数"})

        import os
        if not os.path.exists(db_path):
            return jsonify({
                "success": False,
                "error": "数据库文件不存在",
                "db_path": db_path
            })

        try:
            from services.database_service import DatabaseService
            test_db = DatabaseService(db_path)

            if test_db.check_connection():
                columns = test_db.get_table_info()
                total_records = test_db.get_total_count()

                return jsonify({
                    "success": True,
                    "message": "数据库可用",
                    "db_path": db_path,
                    "table_exists": columns is not None,
                    "total_records": total_records,
                    "columns": columns or []
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "无法连接到数据库",
                    "db_path": db_path
                })
        except Exception as e:
            logger.error(f"测试数据库连接失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "db_path": db_path
            })

    @app.route('/api/db-check', methods=['GET'])
    @api_error_handler
    def check_db_status():
        """实时检查数据库连接状态"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({
                "success": False,
                "error": "监控程序未启动",
                "connection_status": "未连接"
            }), 500

        try:
            connection_status = monitor._check_database_connection()

            details = {
                "db_available": monitor.db_available,
                "db_path": monitor.db_path,
                "connection_status": connection_status,
                "timestamp": monitor.time_utils.get_current_datetime_str()
            }

            if monitor.db_available and monitor.db_service and connection_status == "已连接":
                try:
                    details["total_records"] = monitor.db_service.get_total_count()
                    details["max_id"] = monitor.db_service.get_max_id()
                    details["monitor_last_id"] = monitor.last_id
                except Exception as detail_error:
                    logger.warning(f"获取数据库详细信息失败: {detail_error}")

            return jsonify({
                "success": True,
                **details
            })
        except Exception as e:
            logger.error(f"检查数据库状态失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "connection_status": "连接失败"
            }), 500

    @app.route('/api/config/theme', methods=['GET'])
    @api_error_handler
    def public_theme():
        """公开主题查询 API（无需登录，供登录页使用）"""
        monitor = get_monitor()
        if not monitor:
            return jsonify({"theme": "default"})
        current_theme = monitor.config.get('theme', 'default')
        return jsonify({"theme": current_theme})

    @app.route('/api/theme', methods=['GET', 'POST'])
    @login_required
    @api_error_handler
    def theme():
        """主题管理 API"""
        monitor = get_monitor()
        if not monitor:
            return {"error": "监控程序未启动"}

        if request.method == 'POST':
            new_theme = request.json.get('theme')
            if not new_theme:
                return jsonify({"success": False, "error": "缺少主题参数"})

            try:
                monitor.config['theme'] = new_theme
                success = monitor.update_config({'theme': new_theme})

                if success:
                    logger.info(f"主题已更新为: {new_theme}")
                    return jsonify({"success": True, "theme": new_theme})
                else:
                    return jsonify({"success": False, "error": "主题更新失败"})
            except Exception as e:
                logger.error(f"更新主题时发生异常: {e}")
                return jsonify({"success": False, "error": str(e)})


def register_sponsor_routes(app):
    """注册赞助相关路由"""
    @app.route('/api/sponsor', methods=['GET'])
    def get_sponsor():
        """获取赞助二维码信息"""
        sponsor_config = {
            "title": "感谢您的支持",
            "description": "您的赞助是我持续开发的最大动力",
            "qrcode_url": "/static/images/sponsor_qrcode.png",
            "weixin_url": "/static/images/weixin.jpg",
            "enabled": True
        }
        return jsonify(sponsor_config)
