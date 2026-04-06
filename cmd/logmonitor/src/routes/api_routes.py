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

    def _get_events_file_path():
        """获取事件配置文件路径（优先使用 APP_HOME/config/events.json）"""
        import os
        from pathlib import Path
        
        app_home = os.environ.get('APP_HOME')
        logger.info(f"_get_events_file_path: APP_HOME={app_home}")
        
        if app_home:
            path = Path(app_home) / 'config' / 'events.json'
            logger.info(f"_get_events_file_path: 检查 {path}, exists={path.exists()}")
            if path.exists() or True:  # 允许返回不存在的路径
                return path
        
        # fallback 到源码目录
        src_path = _find_events_json()
        logger.info(f"_get_events_file_path: fallback 到 {src_path}")
        return src_path

    def _load_events_config():
        """加载事件配置"""
        import json
        events_file = _get_events_file_path()
        logger.info(f"_load_events_config: 文件路径={events_file}")
        
        if events_file and events_file.exists():
            try:
                with open(events_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"_load_events_config: 成功加载 {len(config.get('categories', []))} 个分类")
                return config
            except Exception as e:
                logger.error(f"加载事件配置失败: {e}")
        
        # 返回默认结构
        return {"version": "1.0.0", "categories": []}

    def _save_events_config(config):
        """保存事件配置"""
        import json
        events_file = _get_events_file_path()
        
        if events_file:
            events_file.parent.mkdir(parents=True, exist_ok=True)
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        return False

    @app.route('/api/events/list', methods=['GET'])
    @api_error_handler
    def events_list():
        """
        获取事件列表（扁平化所有分类下的事件）
        """
        try:
            logger.info("=== /api/events/list 被调用 ===")
            config = _load_events_config()
            events = []
            for category in config.get('categories', []):
                for event in category.get('events', []):
                    events.append({
                        "id": event.get('id'),
                        "name": event.get('name'),
                        "icon": event.get('icon', 'fa-bell'),
                        "color": event.get('color', '#007bff'),
                        "category": category.get('name'),
                        "category_id": category.get('id')
                    })
            
            logger.info(f"=== 返回 {len(events)} 个事件 ===")
            return jsonify({
                "status": "success",
                "events": events,
                "total": len(events)
            })
        except Exception as e:
            logger.error(f"获取事件列表失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/events/add', methods=['POST'])
    @api_error_handler
    def events_add():
        """
        添加新事件
        """
        try:
            import json
            from flask import request
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "请求数据不能为空"}), 400
            
            event_id = data.get('id', '').strip()
            event_name = data.get('name', '').strip()
            event_icon = data.get('icon', 'fa-bell')
            event_color = data.get('color', '#007bff')
            category_id = data.get('category_id', 'custom')
            
            if not event_id:
                return jsonify({"error": "事件ID不能为空"}), 400
            if not event_name:
                return jsonify({"error": "事件名称不能为空"}), 400
            
            config = _load_events_config()
            
            # 检查事件ID是否已存在
            for cat in config.get('categories', []):
                for evt in cat.get('events', []):
                    if evt.get('id') == event_id:
                        return jsonify({"error": f"事件ID '{event_id}' 已存在"}), 400
            
            # 查找或创建自定义分类
            custom_category = None
            for cat in config.get('categories', []):
                if cat.get('id') == category_id:
                    custom_category = cat
                    break
            
            if not custom_category:
                # 创建新分类
                custom_category = {
                    "id": category_id,
                    "name": data.get('category_name', '自定义事件'),
                    "events": []
                }
                config.setdefault('categories', []).append(custom_category)
            
            # 添加事件
            custom_category['events'].append({
                "id": event_id,
                "name": event_name,
                "icon": event_icon,
                "color": event_color
            })
            
            if _save_events_config(config):
                # 自动将新事件添加到监控列表
                try:
                    from monitor_core import get_monitor
                    monitor = get_monitor()
                    if monitor and monitor.config:
                        event_ids = monitor.config.get('event_ids', [])
                        if event_id not in event_ids:
                            event_ids.append(event_id)
                            monitor.update_config({'event_ids': event_ids})
                            logger.info(f"已将事件 '{event_id}' 自动添加到监控列表")
                except Exception as e:
                    logger.warning(f"自动添加到监控列表失败: {e}")
                
                return jsonify({
                    "status": "success",
                    "message": f"事件 '{event_name}' 添加成功并已启用监控"
                })
            else:
                return jsonify({"error": "保存配置文件失败"}), 500
                
        except Exception as e:
            logger.error(f"添加事件失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/events/delete', methods=['POST'])
    @api_error_handler
    def events_delete():
        """
        删除事件
        """
        try:
            import json
            from flask import request
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "请求数据不能为空"}), 400
            
            event_id = data.get('id', '').strip()
            if not event_id:
                return jsonify({"error": "事件ID不能为空"}), 400
            
            config = _load_events_config()
            
            # 查找并删除事件
            deleted = False
            for cat in config.get('categories', []):
                events = cat.get('events', [])
                for i, evt in enumerate(events):
                    if evt.get('id') == event_id:
                        events.pop(i)
                        deleted = True
                        break
                if deleted:
                    break
            
            if not deleted:
                return jsonify({"error": f"事件ID '{event_id}' 不存在"}), 404
            
            if _save_events_config(config):
                return jsonify({
                    "status": "success",
                    "message": f"事件 '{event_id}' 已删除"
                })
            else:
                return jsonify({"error": "保存配置文件失败"}), 500
                
        except Exception as e:
            logger.error(f"删除事件失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/events/update', methods=['POST'])
    @api_error_handler
    def events_update():
        """
        更新事件
        """
        try:
            import json
            from flask import request
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "请求数据不能为空"}), 400
            
            event_id = data.get('id', '').strip()
            event_name = data.get('name', '').strip()
            event_icon = data.get('icon', 'fa-bell')
            event_color = data.get('color', '#007bff')
            
            if not event_id:
                return jsonify({"error": "事件ID不能为空"}), 400
            
            config = _load_events_config()
            
            # 查找并更新事件
            found = False
            for cat in config.get('categories', []):
                for evt in cat.get('events', []):
                    if evt.get('id') == event_id:
                        evt['name'] = event_name
                        evt['icon'] = event_icon
                        evt['color'] = event_color
                        found = True
                        break
                if found:
                    break
            
            if not found:
                return jsonify({"error": f"事件ID '{event_id}' 不存在"}), 404
            
            if _save_events_config(config):
                return jsonify({
                    "status": "success",
                    "message": f"事件 '{event_id}' 已更新"
                })
            else:
                return jsonify({"error": "保存配置文件失败"}), 500
                
        except Exception as e:
            logger.error(f"更新事件失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/events/categories', methods=['GET'])
    @api_error_handler
    def events_categories():
        """
        获取事件分类列表
        """
        try:
            config = _load_events_config()
            categories = []
            for cat in config.get('categories', []):
                categories.append({
                    "id": cat.get('id'),
                    "name": cat.get('name'),
                    "event_count": len(cat.get('events', []))
                })
            
            return jsonify({
                "status": "success",
                "categories": categories
            })
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/events/query-latest', methods=['GET'])
    @api_error_handler
    def events_query_latest():
        """
        根据事件ID查询数据库中该事件的最新一条记录
        """
        try:
            from flask import request
            from monitor_core import get_monitor
            from utils.time_utils import TimeUtils
            
            event_id = request.args.get('event_id', '').strip()
            if not event_id:
                return jsonify({"error": "事件ID不能为空"}), 400
            
            monitor = get_monitor()
            if not monitor or not monitor.db_available or not monitor.db_service:
                return jsonify({"error": "数据库未连接"}), 500
            
            # 使用上下文管理器获取数据库连接
            with monitor.db_service.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, logtime, loglevel, category, eventId, serviceId, uname, parameter
                    FROM log 
                    WHERE eventId = ? 
                    ORDER BY id DESC 
                    LIMIT 1
                """, (event_id,))
                row = cursor.fetchone()
                
                if row:
                    # 使用 TimeUtils 转换时间戳为上海时区时间
                    logtime_str = TimeUtils.timestamp_to_shanghai(row[1]) if row[1] else ""
                    result = {
                        "id": row[0],
                        "logtime": row[1],
                        "logtime_str": logtime_str,
                        "loglevel": row[2],
                        "category": row[3],
                        "eventId": row[4],
                        "serviceId": row[5],
                        "uname": row[6],
                        "parameter": row[7]
                    }
                    return jsonify({
                        "status": "success",
                        "found": True,
                        "log": result
                    })
                else:
                    return jsonify({
                        "status": "success",
                        "found": False,
                        "message": f"数据库中未找到事件ID '{event_id}' 的记录"
                    })
                
        except Exception as e:
            logger.error(f"查询事件记录失败: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return app
