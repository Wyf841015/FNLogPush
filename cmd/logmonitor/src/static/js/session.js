// ========== session.js - Session管理和通知模块 ==========

// ========== Session 状态 ==========
let sessionCheckInterval = null;
let lastActivityTime = Date.now();

// ========== Session 管理函数 ==========

/**
 * 刷新活动时间
 */
async function refreshActivity() {
    try {
        const response = await apiFetch('/api/auth/refresh-activity', { method: 'POST' });
        if (!response.ok) {
            console.log('Session已过期，请重新登录');
            window.location.reload();
        }
    } catch (e) {
        console.error('刷新活动时间失败:', e);
    }
}

/**
 * 设置活动检测
 */
function setupActivityDetection() {
    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    
    activityEvents.forEach(event => {
        document.addEventListener(event, () => {
            lastActivityTime = Date.now();
        }, { passive: true });
    });
}

/**
 * 启动Session检查
 */
function startSessionCheck() {
    if (sessionCheckInterval) clearInterval(sessionCheckInterval);
    
    // 启动活动检测
    setupActivityDetection();
    
    // 每分钟检查一次无操作时间
    sessionCheckInterval = setInterval(async () => {
        const idleTime = (Date.now() - lastActivityTime) / 1000; // 秒
        if (idleTime > 300) { // 5分钟无操作
            console.log('无操作超过5分钟，退出登录');
            window.location.href = '/logout';
            return;
        }
        
        // 有操作时刷新活动时间
        try {
            await refreshActivity();
        } catch (e) {
            console.error('Session检查失败:', e);
        }
    }, 60 * 1000); // 每分钟检查
}

// ========== 通知管理器 ==========

const NotificationManager = {
    container: null,
    
    /**
     * 获取容器
     */
    getContainer() {
        if (!this.container) {
            this.container = document.getElementById('notification-container');
        }
        return this.container;
    },
    
    /**
     * 获取当前时间字符串
     */
    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('zh-CN', { hour12: false });
    },
    
    /**
     * 显示通知
     * @param {string} title - 标题
     * @param {string} message - 消息内容
     * @param {string} type - 类型 (success/error/warning/info)
     * @param {number} duration - 显示时长（毫秒）
     */
    showNotification(title, message, type = 'info', duration = 5000) {
        const container = this.getContainer();
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        notification.innerHTML = `
            <div class="notification-header">
                <div class="notification-title">${title}</div>
                <button class="notification-close" onclick="NotificationManager.closeNotification(this)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="notification-message">${message}</div>
            <div class="notification-time">${this.getCurrentTime()}</div>
        `;
        
        container.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                this.closeNotification(notification);
            }, duration);
        }
    },
    
    /**
     * 关闭通知
     * @param {HTMLElement} element - 通知元素或其关闭按钮
     */
    closeNotification(element) {
        const notification = element.closest ? element.closest('.notification') : element;
        if (notification) {
            notification.classList.add('closing');
            setTimeout(() => notification.remove(), 300);
        }
    },
    
    /**
     * 成功通知
     */
    success(title, message, duration) {
        this.showNotification(title, message, 'success', duration);
    },
    
    /**
     * 错误通知
     */
    error(title, message, duration) {
        this.showNotification(title, message, 'error', duration);
    },
    
    /**
     * 警告通知
     */
    warning(title, message, duration) {
        this.showNotification(title, message, 'warning', duration);
    },
    
    /**
     * 信息通知
     */
    info(title, message, duration) {
        this.showNotification(title, message, 'info', duration);
    }
};

/**
 * 测试浏览器通知权限
 */
function testNotification() {
    if (!('Notification' in window)) {
        NotificationManager.warning('不支持通知', '您的浏览器不支持通知功能');
        return;
    }
    
    if (Notification.permission === 'granted') {
        new Notification('测试通知', {
            body: '浏览器通知功能正常！',
            icon: '/static/images/icon-64.png'
        });
        NotificationManager.success('通知测试', '浏览器通知权限已授予');
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                new Notification('测试通知', {
                    body: '浏览器通知功能正常！',
                    icon: '/static/images/icon-64.png'
                });
                NotificationManager.success('通知测试', '已授权浏览器通知');
            } else {
                NotificationManager.warning('通知测试', '浏览器通知权限被拒绝');
            }
        });
    } else {
        NotificationManager.warning('通知测试', '浏览器通知权限已被拒绝，请在设置中开启');
    }
}

/**
 * 测试推送通知（通过API）
 */
function testPushNotification() {
    const notification = new Notification('FNOS日志监控', {
        body: '这是一条测试推送通知！',
        icon: '/static/images/icon-64.png',
        tag: 'test-notification'
    });
    
    notification.onclick = function() {
        window.focus();
        notification.close();
    };
}

// ========== 导出到全局 ==========
window.refreshActivity = refreshActivity;
window.setupActivityDetection = setupActivityDetection;
window.startSessionCheck = startSessionCheck;
window.NotificationManager = NotificationManager;
window.testNotification = testNotification;
window.testPushNotification = testPushNotification;
