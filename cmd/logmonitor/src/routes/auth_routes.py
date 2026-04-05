#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证相关路由模块
处理用户登录、注册、登出等认证功能
"""
from flask import Flask, request, jsonify, session
import logging
import time

from services.auth_service import AuthService
from utils import api_error_handler
from utils.auth import login_required  # 统一出口

logger = logging.getLogger(__name__)

# 初始化认证服务（auth_routes 是唯一持有 AuthService 实例的路由模块）
auth_service = AuthService()


def register_auth_routes(app: Flask):
    """
    注册认证相关路由

    Args:
        app: Flask应用实例
    """

    @app.route('/api/auth/check-setup', methods=['GET'])
    @api_error_handler
    def check_setup():
        """检查是否需要初始设置"""
        is_first_run = auth_service.is_first_run()
        return jsonify({
            'need_setup': is_first_run,
            'username': auth_service.get_username() if not is_first_run else None
        })

    @app.route('/api/auth/setup', methods=['POST'])
    @api_error_handler
    def setup_auth():
        """设置初始用户名和密码"""
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')

        success, message = auth_service.setup_initial_user(username, password)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    @app.route('/api/auth/login', methods=['POST'])
    @api_error_handler
    def login():
        """用户登录"""
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')

        success, message = auth_service.verify_login(username, password)
        if success:
            # 设置永久session
            session['user'] = username
            session['login_time'] = time.time()
            session['last_activity'] = time.time()
            session.permanent = True
            logger.info(f"用户登录成功: {username}")
            return jsonify({'success': True, 'message': message, 'username': username})
        else:
            logger.warning(f"用户登录失败: {username}, 原因: {message}")
            return jsonify({'success': False, 'error': message}), 401

    @app.route('/api/auth/logout', methods=['POST'])
    @api_error_handler
    def logout():
        """用户退出"""
        username = session.get('user')
        # 清除整个session
        session.clear()
        if username:
            logger.info(f"用户登出: {username}")
        return jsonify({'success': True, 'message': '退出成功'})

    @app.route('/api/auth/check-session', methods=['GET'])
    @api_error_handler
    def check_session():
        """检查会话状态"""
        if 'user' in session:
            # 更新活动时间
            session['last_activity'] = time.time()
            return jsonify({
                'logged_in': True,
                'username': session['user']
            })
        return jsonify({
            'logged_in': False,
            'username': None
        })

    @app.route('/api/auth/refresh-activity', methods=['POST'])
    @api_error_handler
    def refresh_activity():
        """刷新活动时间（用于前端保持登录状态）"""
        if 'user' in session:
            session['last_activity'] = time.time()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '未登录'}), 401

    @app.route('/api/auth/change-password', methods=['POST'])
    @login_required
    @api_error_handler
    def change_password():
        """修改密码"""
        data = request.json
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        if not old_password or not new_password:
            return jsonify({'success': False, 'error': '缺少密码参数'}), 400

        success, message = auth_service.change_password(old_password, new_password)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400

    return app
