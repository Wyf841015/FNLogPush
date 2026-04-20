"""
相册监控API路由
"""

import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

photo_bp = Blueprint('photo', __name__, url_prefix='/api/photo')


def init_photo_routes(app, config_manager, photo_monitor):
    """初始化相册监控路由"""
    
    @photo_bp.route('/status', methods=['GET'])
    def get_photo_status():
        """获取相册监控状态"""
        try:
            status = photo_monitor.get_status()
            return jsonify({'code': 0, 'data': status})
        except Exception as e:
            logger.error(f"获取相册状态失败: {e}")
            return jsonify({'code': 1, 'msg': str(e)}), 500

    @photo_bp.route('/config', methods=['GET', 'POST'])
    def photo_config():
        """相册监控配置"""
        if request.method == 'GET':
            try:
                media_config = config_manager.get('photo_monitor', {})
                return jsonify({'code': 0, 'data': media_config})
            except Exception as e:
                logger.error(f"获取相册配置失败: {e}")
                return jsonify({'code': 1, 'msg': str(e)}), 500
        
        # POST - 保存配置
        try:
            config = request.json or {}
            photo_monitor.update_config(
                db_path=config.get('db_path', photo_monitor.db_path),
                poll_interval=config.get('poll_interval', photo_monitor.poll_interval),
                monitor_events=config.get('monitor_events', photo_monitor.monitor_events)
            )
            
            # 保存到配置文件
            photo_config = {
                'enabled': config.get('enabled', False),
                'db_path': config.get('db_path', photo_monitor.db_path),
                'poll_interval': config.get('poll_interval', 10),
                'monitor_events': config.get('monitor_events', list(photo_monitor.monitor_events) if photo_monitor.monitor_events else [])
            }
            config_manager.set('photo_monitor', photo_config)
            config_manager.save()
            
            return jsonify({'code': 0, 'msg': '配置已保存'})
        except Exception as e:
            logger.error(f"保存相册配置失败: {e}")
            return jsonify({'code': 1, 'msg': str(e)}), 500

    @photo_bp.route('/events', methods=['GET'])
    def get_photo_events():
        """获取相册事件"""
        try:
            limit = int(request.args.get('limit', 50))
            event_type = request.args.get('type')
            events = app.photo_event_service.get_events(limit=limit, event_type=event_type)
            return jsonify({'code': 0, 'data': events})
        except Exception as e:
            logger.error(f"获取相册事件失败: {e}")
            return jsonify({'code': 1, 'msg': str(e)}), 500

    @photo_bp.route('/toggle', methods=['POST'])
    def toggle_photo_monitor():
        """启用/禁用相册监控"""
        try:
            data = request.json or {}
            enabled = data.get('enabled', False)
            
            if enabled:
                photo_monitor.start()
            else:
                photo_monitor.stop()
            
            # 更新配置
            photo_config = config_manager.get('photo_monitor', {})
            photo_config['enabled'] = enabled
            config_manager.set('photo_monitor', photo_config)
            config_manager.save()
            
            return jsonify({'code': 0, 'msg': '操作成功', 'data': {'enabled': enabled}})
        except Exception as e:
            logger.error(f"切换相册监控失败: {e}")
            return jsonify({'code': 1, 'msg': str(e)}), 500

    app.register_blueprint(photo_bp)
    logger.info("✓ 相册监控路由已注册")
