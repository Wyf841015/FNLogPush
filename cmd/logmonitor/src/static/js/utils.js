// ========== utils.js - 工具函数模块 ==========

// ========== 全局事件配置缓存 ==========
let eventCategoriesCache = null;

// 从API加载事件配置（带缓存）
async function loadEventCategoriesFromAPI() {
    if (eventCategoriesCache) return eventCategoriesCache;
    
    try {
        const response = await fetch('/api/events/config');
        if (response.ok) {
            const data = await response.json();
            if (data.config && data.config.categories) {
                const categories = {};
                data.config.categories.forEach(cat => {
                    categories[cat.name] = cat.events.map(e => ({
                        id: e.id,
                        icon: e.icon || 'fa-circle',
                        color: e.color || '#667eea',
                        name: e.name || e.id
                    }));
                });
                eventCategoriesCache = categories;
                return categories;
            }
        }
    } catch (err) {
        console.warn('从API加载事件配置失败:', err);
    }
    return null;
}

// ========== 常量定义 ==========
const CONSTANTS = {
    // 状态常量
    DB_STATUS: {
        CONNECTED: '已连接',
        FAILED: '连接失败',
        DISCONNECTED: '未连接'
    },
    // 刷新间隔（毫秒）
    REFRESH_INTERVAL: {
        HEALTH: 15000,
        AUTO: 30000,
        SESSION: 60000
    },
    // Session 超时（秒）
    SESSION_TIMEOUT: 300,
    // 通知持续时间（毫秒）
    NOTIFICATION_DURATION: 5000
};

// ========== 通用工具函数 ==========

/**
 * 格式化相对时间
 * @param {number} timestamp - Unix 时间戳（秒）
 * @returns {string} 相对时间字符串
 */
function formatRelativeTime(timestamp) {
    if (!timestamp) return '未知';
    
    const now = Math.floor(Date.now() / 1000);
    const diff = now - timestamp;
    
    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`;
    
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN', { hour12: false });
}

/**
 * HTML转义，防止XSS
 * @param {string} text - 原始文本
 * @returns {string} 转义后的文本
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 显示通知消息
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success/error/warning/info)
 */
function showNotification(message, type = 'info') {
    // 移除已存在的通知
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();
    
    const colors = {
        success: 'linear-gradient(135deg, #10b981, #059669)',
        error: 'linear-gradient(135deg, #ef4444, #dc2626)',
        warning: 'linear-gradient(135deg, #f59e0b, #d97706)',
        info: 'linear-gradient(135deg, #3b82f6, #2563eb)'
    };
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    const notification = document.createElement('div');
    notification.className = 'toast-notification';
    notification.style.cssText = `
        position: fixed;
        top: 70px;
        right: 20px;
        background: ${colors[type] || colors.info};
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        animation: slideIn 0.3s ease;
        max-width: 400px;
    `;
    notification.innerHTML = `
        <i class="fas ${icons[type] || icons.info}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, CONSTANTS.NOTIFICATION_DURATION || 5000);
}

/**
 * 关键词高亮
 * @param {string} text - 原始文本
 * @param {string} kw - 关键词
 * @returns {string} 高亮后的HTML
 */
function highlightKeyword(text, kw) {
    if (!kw || !text) return text;
    const regex = new RegExp(`(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark style="background:#fef08a;padding:0 2px;border-radius:2px;">$1</mark>');
}

/**
 * 数字滚动动画
 * @param {HTMLElement} element - DOM元素
 * @param {string} newValue - 新值
 */
function animateNumber(element, newValue) {
    if (!element) return;
    
    const oldValue = element.textContent;
    if (oldValue === newValue) return;
    
    element.classList.add('animating');
    element.textContent = newValue;
    
    setTimeout(() => {
        element.classList.remove('animating');
    }, 400);
}

/**
 * 防抖函数
 * @param {Function} func - 要执行的函数
 * @param {number} wait - 等待时间（毫秒）
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 * @param {Function} func - 要执行的函数
 * @param {number} limit - 时间限制（毫秒）
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 导出到全局
window.loadEventCategoriesFromAPI = loadEventCategoriesFromAPI;
window.CONSTANTS = CONSTANTS;
window.formatRelativeTime = formatRelativeTime;
window.escapeHtml = escapeHtml;
window.showNotification = showNotification;
window.highlightKeyword = highlightKeyword;
window.animateNumber = animateNumber;
window.debounce = debounce;
window.throttle = throttle;
