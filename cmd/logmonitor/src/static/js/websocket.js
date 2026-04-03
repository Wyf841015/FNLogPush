// ========== WebSocket 实时推送管理器 ==========

class WebSocketManager {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 3000;
        this.pingInterval = null;
        this.pingDelay = 30000;
        this.listeners = {};
        this._init();
    }

    _init() {
        // 连接状态变化回调
        this.onConnected = null;
        this.onDisconnected = null;
        this.onNewLogs = null;
        this.onPushResult = null;
    }

    connect() {
        if (this.socket && this.connected) return;

        // 构建 WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/socket.io/?EIO=4&transport=websocket`;

        try {
            this.socket = io(wsUrl, {
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay
            });

            this.socket.on('connect', () => {
                console.log('WebSocket已连接');
                this.connected = true;
                this.reconnectAttempts = 0;
                this._emit('connected');
                this.startPing();
                if (this.onConnected) this.onConnected();
            });

            this.socket.on('disconnect', () => {
                console.log('WebSocket已断开');
                this.connected = false;
                this.stopPing();
                this._emit('disconnected');
                if (this.onDisconnected) this.onDisconnected();
            });

            this.socket.on('connect_error', (error) => {
                console.error('WebSocket连接错误:', error);
                this.reconnectAttempts++;
            });

            // 监听新日志事件
            this.socket.on('new_logs', (data) => {
                console.log('收到新日志推送:', data.count);
                this._emit('new_logs', data);
                if (this.onNewLogs) this.onNewLogs(data);
            });

            // 监听推送结果事件
            this.socket.on('push_result', (data) => {
                console.log('收到推送结果:', data);
                this._emit('push_result', data);
                if (this.onPushResult) this.onPushResult(data);
            });

            // 监听ping响应
            this.socket.on('pong', () => {
                console.log('收到pong响应');
            });

        } catch (error) {
            console.error('WebSocket初始化失败:', error);
        }
    }

    disconnect() {
        this.stopPing();
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
            this.connected = false;
        }
    }

    startPing() {
        this.stopPing();
        this.pingInterval = setInterval(() => {
            if (this.connected) {
                this.socket.emit('ping');
            }
        }, this.pingDelay);
    }

    stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    subscribe(event) {
        if (this.socket && this.connected) {
            this.socket.emit('subscribe', { event });
        }
    }

    unsubscribe(event) {
        if (this.socket && this.connected) {
            this.socket.emit('unsubscribe', { event });
        }
    }

    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    _emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => callback(data));
        }
    }

    isConnected() {
        return this.connected;
    }
}

// 全局 WebSocket 管理器
const wsManager = new WebSocketManager();
