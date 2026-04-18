#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket管理器
管理所有WebSocket连接、消息发送和事件广播
"""
import logging
from datetime import datetime
from threading import Lock
from typing import Dict, Callable, Optional, Any

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        """初始化WebSocket管理器"""
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.socketio = None
        self.subscriptions: Dict[str, set] = {}  # 事件订阅映射
    
    def register_socketio(self, socketio):
        """注册SocketIO实例"""
        self.socketio = socketio
        logger.info("WebSocket管理器已初始化")
    
    def connect(self, sid: str, session_data: dict = None):
        """处理客户端连接"""
        with self.lock:
            self.connections[sid] = {
                'connected_at': datetime.now(),
                'session_data': session_data or {},
                'subscriptions': set()
            }
        logger.debug(f"WebSocket客户端连接: {sid}")
    
    def disconnect(self, sid: str):
        """处理客户端断开连接"""
        with self.lock:
            if sid in self.connections:
                del self.connections[sid]
            # 清理订阅
            for event_subs in self.subscriptions.values():
                event_subs.discard(sid)
        logger.debug(f"WebSocket客户端断开: {sid}")
    
    def subscribe(self, sid: str, event: str):
        """订阅事件"""
        with self.lock:
            if event not in self.subscriptions:
                self.subscriptions[event] = set()
            self.subscriptions[event].add(sid)
            
            if sid in self.connections:
                self.connections[sid]['subscriptions'].add(event)
        
        logger.debug(f"客户端 {sid} 订阅事件: {event}")
    
    def unsubscribe(self, sid: str, event: str):
        """取消订阅事件"""
        with self.lock:
            if event in self.subscriptions:
                self.subscriptions[event].discard(sid)
            
            if sid in self.connections:
                self.connections[sid]['subscriptions'].discard(event)
        
        logger.debug(f"客户端 {sid} 取消订阅事件: {event}")
    
    def handle_pong(self, sid: str):
        """处理心跳响应"""
        with self.lock:
            if sid in self.connections:
                self.connections[sid]['last_pong'] = datetime.now()
    
    def emit_to_client(self, sid: str, event: str, data: dict = None):
        """向单个客户端发送事件"""
        if self.socketio and sid in self.connections:
            try:
                self.socketio.emit(event, data, to=sid)
                logger.debug(f"向客户端 {sid} 发送事件: {event}")
            except Exception as e:
                logger.error(f"发送事件到客户端 {sid} 失败: {e}")
    
    def broadcast(self, event: str, data: dict = None):
        """广播事件到所有连接的客户端"""
        if self.socketio:
            try:
                self.socketio.emit(event, data)
                logger.debug(f"广播事件: {event}, 客户端数: {len(self.connections)}")
            except Exception as e:
                logger.error(f"广播事件 {event} 失败: {e}")
    
    def broadcast_to_subscribers(self, event: str, data: dict = None):
        """仅向该事件的订阅者广播"""
        if event not in self.subscriptions:
            return
        
        subscribers = self.subscriptions[event].copy()
        for sid in subscribers:
            self.emit_to_client(sid, event, data)
        
        logger.debug(f"向事件 {event} 的 {len(subscribers)} 个订阅者广播")
    
    def get_connected_clients_count(self) -> int:
        """获取连接的客户端数量"""
        with self.lock:
            return len(self.connections)
    
    def get_client_info(self, sid: str) -> Optional[dict]:
        """获取客户端信息"""
        with self.lock:
            return self.connections.get(sid)
    
    def get_all_clients(self) -> list:
        """获取所有连接的客户端列表"""
        with self.lock:
            return list(self.connections.keys())
    
    def broadcast_health_status(self, health_data: dict):
        """广播健康状态到所有客户端（仅推送给订阅者）"""
        try:
            # 定义健康状态事件名称
            event_name = 'health_status'
            
            # 如果有订阅者，只推送给订阅者
            if event_name in self.subscriptions and self.subscriptions[event_name]:
                self.broadcast_to_subscribers(event_name, health_data)
                logger.debug(f"健康状态已推送给 {len(self.subscriptions[event_name])} 个订阅者")
            elif self.connections:
                # 如果没有订阅者但有连接，也广播（兼容旧客户端）
                self.broadcast(event_name, health_data)
                logger.debug(f"健康状态已广播给 {len(self.connections)} 个客户端")
        except Exception as e:
            logger.error(f"广播健康状态失败: {e}")


# 全局WebSocket管理器实例
_ws_manager = None


def get_websocket_manager() -> WebSocketManager:
    """获取全局WebSocket管理器实例"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


def reset_websocket_manager():
    """重置WebSocket管理器（测试用）"""
    global _ws_manager
    _ws_manager = None
