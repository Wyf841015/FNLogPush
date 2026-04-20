#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""影视监控路由"""

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

media_bp = Blueprint('media', __name__, url_prefix='/api/media')


def init_media_routes(app, config_manager, media_monitor_service):
    """初始化影视监控路由"""
    
    @media_bp.route('/status', methods=['GET'])
    def get_status():
        """获取影视监控状态"""
        stats = media_monitor_service.get_stats()
        return jsonify({
            "code": 0,
            "data": stats
        })
    
    @media_bp.route('/config', methods=['GET'])
    def get_config():
        """获取影视监控配置"""
        config = config_manager.config.get('media_monitor', {})
        return jsonify({
            "code": 0,
            "data": config
        })
    
    @media_bp.route('/config', methods=['POST'])
    def update_config():
        """更新影视监控配置"""
        data = request.get_json()
        if not data:
            return jsonify({"code": 1, "message": "无效的请求数据"}), 400
        
        try:
            # 获取当前配置
            current = config_manager.config.get('media_monitor', {})
            
            # 更新配置
            new_config = {
                "enabled": data.get('enabled', current.get('enabled', False)),
                "db_path": data.get('db_path', current.get('db_path', '/usr/local/apps/@appdata/trim.media/database/trimmedia.db')),
                "activity_db_path": data.get('activity_db_path', current.get('activity_db_path', '/usr/local/apps/@appdata/trim.media/database/trimactivity.db')),
                "poll_interval": data.get('poll_interval', current.get('poll_interval', 10)),
                "monitor_events": data.get('monitor_events', current.get('monitor_events', []))
            }
            
            # 保存配置
            config_manager.config['media_monitor'] = new_config
            config_manager.save()
            
            # 更新监控服务
            media_monitor_service.update_config(
                db_path=new_config['db_path'],
                activity_db_path=new_config['activity_db_path'],
                poll_interval=new_config['poll_interval'],
                monitor_events=new_config['monitor_events']
            )
            
            # 根据启用状态启动/停止监控
            if new_config['enabled'] and not media_monitor_service.running:
                media_monitor_service.start()
            elif not new_config['enabled'] and media_monitor_service.running:
                media_monitor_service.stop()
            
            return jsonify({
                "code": 0,
                "message": "配置已更新",
                "data": new_config
            })
            
        except Exception as e:
            logger.error(f"更新影视监控配置失败: {e}")
            return jsonify({"code": 1, "message": f"更新失败: {str(e)}"}), 500
    
    @media_bp.route('/events', methods=['GET'])
    def get_events():
        """获取影视监控事件列表"""
        from services.media_event_service import MediaEventService
        event_service = MediaEventService()
        events = event_service.get_recent_events(limit=50)
        return jsonify({
            "code": 0,
            "data": events
        })
    
    @media_bp.route('/toggle', methods=['POST'])
    def toggle():
        """启用/禁用影视监控"""
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        try:
            config = config_manager.config.get('media_monitor', {})
            config['enabled'] = enabled
            config_manager.config['media_monitor'] = config
            config_manager.save()
            
            if enabled and not media_monitor_service.running:
                media_monitor_service.start()
            elif not enabled and media_monitor_service.running:
                media_monitor_service.stop()
            
            return jsonify({
                "code": 0,
                "message": "切换成功" if enabled else "已禁用"
            })
        except Exception as e:
            return jsonify({"code": 1, "message": str(e)}), 500
