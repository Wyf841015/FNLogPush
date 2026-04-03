#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证工具模块
提供统一的 login_required 装饰器，避免在各路由模块中重复定义
"""
from functools import wraps
from flask import session, jsonify


def login_required(f):
    """登录验证装饰器 —— 统一出口，各路由模块直接从此处导入"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'success': False, 'error': '未登录，请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function
