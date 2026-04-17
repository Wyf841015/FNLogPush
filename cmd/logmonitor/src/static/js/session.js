// ========== session.js - Session管理和通知模块 ==========

// 注意：以下变量已在 main.js 中定义，此处引用
// let sessionCheckInterval = null;
// let lastActivityTime = Date.now();

// ========== Session 管理函数 ==========

/**
 * 用户登出
 */
async function logout() {
    try {
        await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {
        console.error('登出请求失败:', e);
    }
    // 清除本地存储
    localStorage.clear();
    // 重定向到登录页
    window.location.href = '/login';
}

/**
 * 刷新活动时间（使用现有接口）
 */
async function refreshActivity() {
    try {
        // 使用 /api/auth/status 接口来保持session活跃
        const response = await apiFetch('/api/auth/status');
        if (!response.ok) {
            console.log('Session已过期，请重新登录');
            window.location.href = '/login';
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
// 注意：NotificationManager 已在 main.js 中定义，避免重复声明冲突

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
window.logout = logout;
