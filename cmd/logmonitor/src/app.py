#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用入口点
统一的启动脚本

适配飞牛NAS原生应用
"""
import sys
import io
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 获取应用代码目录
MAIN_FILE = Path(__file__).resolve()
SRC_DIR = MAIN_FILE.parent
CODE_DIR = SRC_DIR.parent

# 添加到Python路径
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(SRC_DIR))

# 获取应用主目录
APP_HOME = os.environ.get('APP_HOME', str(CODE_DIR))
LOG_DIR = Path(APP_HOME) / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 设置标准输入输出编码为UTF-8
if sys.platform != 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置日志
log_file = LOG_DIR / 'app.log'
file_handler = RotatingFileHandler(log_file, maxBytes=1048576, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, stream_handler]
)

logger = logging.getLogger(__name__)

from flask import Flask
from flask_socketio import SocketIO

# 初始化SocketIO
socketio = SocketIO()


def create_app():
    """创建Flask应用"""
    template_dir = SRC_DIR / 'templates'
    static_dir = SRC_DIR / 'static'
    
    app = Flask(__name__,
                template_folder=str(template_dir),
                static_folder=str(static_dir))

    # Secret Key - 使用固定的密钥，确保session持久化
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        # 使用固定的密钥，确保重启后session仍然有效
        secret_key = 'fnlogpush-secret-key-2024'
    app.secret_key = secret_key

    # Session 配置 - 确保 cookie 正确工作
    app.config['SESSION_COOKIE_NAME'] = 'fnlogpush_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # 允许 HTTP
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 允许正常导航
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7天
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # 每次请求刷新session过期时间
    
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False

    # 初始化SocketIO
    socketio.init_app(app, cors_allowed_origins='*', async_mode='threading')

    # 注册所有路由
    from routes import register_all_routes
    register_all_routes(app)

    # 注册WebSocket事件
    from websocket_manager import get_websocket_manager
    ws_manager = get_websocket_manager()
    ws_manager.register_socketio(socketio)

    # 注册WebSocket事件处理器
    register_websocket_events(socketio, ws_manager)

    logger.info("Flask应用创建成功")
    return app


def register_websocket_events(socketio, ws_manager):
    """注册WebSocket事件"""
    @socketio.on('connect')
    def handle_connect(auth=None):
        from flask import request, session
        sid = request.sid
        session_data = dict(session) if 'user' in session else {}
        ws_manager.connect(sid, session_data)
        logger.info(f"WebSocket连接: {sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        from flask import request
        sid = request.sid
        ws_manager.disconnect(sid)
        logger.info(f"WebSocket断开: {sid}")

    @socketio.on('message')
    def handle_message(data):
        from flask import request
        sid = request.sid
        logger.debug(f"收到WebSocket消息: {sid}, data: {data}")

    @socketio.on('subscribe')
    def handle_subscribe(data):
        from flask import request
        sid = request.sid
        event = data.get('event')
        if event:
            logger.debug(f"客户端订阅事件: {sid}, event: {event}")

    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        from flask import request
        sid = request.sid
        event = data.get('event')
        if event:
            logger.debug(f"客户端取消订阅事件: {sid}, event: {event}")

    @socketio.on('pong')
    def handle_pong(data):
        from flask import request
        sid = request.sid
        ws_manager.handle_pong(sid)
        logger.debug(f"收到pong响应: {sid}")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("FNOS日志监控推送系统")
    logger.info("=" * 50)
    logger.info(f"源码目录: {SRC_DIR}")
    logger.info(f"APP_HOME: {APP_HOME}")

    # 设置配置文件绝对路径
    config_dir = Path(APP_HOME) / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / 'config.json'
    
    # 如果配置文件不存在，从源码目录复制
    if not config_file.exists():
        src_config = SRC_DIR / 'config.json'
        if src_config.exists():
            import shutil
            shutil.copy(src_config, config_file)
            logger.info(f"配置文件已复制到: {config_file}")

    # 设置工作目录为APP_HOME，确保相对路径配置正确
    os.chdir(APP_HOME)
    logger.info(f"工作目录: {os.getcwd()}")

    # 创建Flask应用
    app = create_app()

    # 尝试初始化监控服务
    try:
        from monitor_core import LogMonitor, get_monitor
        # 先获取或创建monitor实例（设置全局实例）
        monitor = get_monitor()
        if monitor:
            monitor.start()
            if monitor.running:
                logger.info("✓ 监控服务已启动")
            else:
                logger.warning("⚠ 监控服务启动失败")
        else:
            logger.warning("⚠ 监控服务获取失败")
    except Exception as e:
        logger.warning(f"监控服务初始化跳过: {e}")

    # 获取端口 - 优先从环境变量
    port = int(os.environ.get('UI_PORT', 19800))
    host = '0.0.0.0'

    logger.info(f"✓ Web服务地址: http://{host}:{port}")
    logger.info("✓ WebSocket支持已启用")
    logger.info("=" * 50)

    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
