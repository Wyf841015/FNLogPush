#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes 包初始化文件

该包包含系统的路由模块，包括：
- 认证路由：处理用户登录、注册、登出等
- 监控路由：处理监控状态、配置、控制等
- 备份路由：处理备份数据库监控
- 通用API路由：处理健康检查等
"""
from flask import Flask, render_template, session, make_response
from functools import wraps
from .auth_routes import register_auth_routes
from .monitor_routes import register_monitor_routes, register_sponsor_routes
from .backup_routes import register_backup_routes
from .api_routes import register_api_routes


def check_session(f):
    """检查session装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 如果session中没有user，重定向到登录页
        if 'user' not in session:
            return render_template('login.html')
        return f(*args, **kwargs)
    return decorated_function


def register_all_routes(app: Flask):
    """
    注册所有路由

    Args:
        app: Flask应用实例
    """

    # 页面路由
    @app.route('/')
    @check_session
    def index():
        """Web界面"""
        return render_template('index.html')

    @app.route('/login')
    def login_page():
        """登录页面"""
        # 如果已经登录，直接跳转到主页
        if 'user' in session:
            return render_template('index.html')
        return render_template('login.html')

    @app.route('/logout')
    def logout_page():
        """退出页面"""
        session.clear()
        return render_template('login.html')

    # 注册各个模块的路由
    register_auth_routes(app)
    register_monitor_routes(app)
    register_sponsor_routes(app)
    register_backup_routes(app)
    register_api_routes(app)

    return app


__all__ = [
    'register_all_routes',
    'register_auth_routes',
    'register_monitor_routes',
    'register_backup_routes',
    'register_api_routes'
]
