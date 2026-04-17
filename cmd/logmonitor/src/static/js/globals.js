// ========== globals.js - 全局变量定义 ==========
// 此文件必须第一个加载，包含所有全局变量

// ========== 全局状态 ==========
let currentConfig = {};
let eventCategoriesCache = null;
let sessionCheckInterval = null;
let activityRefreshInterval = null;
let lastActivityTime = Date.now();
let healthUpdateInterval = null;
let autoRefreshInterval = null;
let sidebarOpen = false;
let sidebarCollapsed = false;

// ========== 历史记录相关 ==========
let lastHistoryIndex = null;
let _historySearchTimer = null;
let historyKeyword = '';
let historyCurrentPage = 1;
const historyPageSize = 20;
let historyTotal = 0;
let historyDateFilter = {
    startDate: '',
    endDate: ''
};

// ========== 常量 ==========
const CONSTANTS = {
    DB_STATUS: {
        CONNECTED: '已连接',
        FAILED: '连接失败',
        DISCONNECTED: '未连接'
    },
    REFRESH_INTERVAL: {
        HEALTH: 15000,
        AUTO: 30000,
        SESSION: 60000
    },
    SESSION_TIMEOUT: 300,
    NOTIFICATION_DURATION: 5000
};

const DEFAULT_REFRESH_INTERVAL = 10000;

// ========== 管理器 ==========
const NotificationManager = {
    container: document.getElementById('notification-container'),
    
    showNotification(title, message, type = 'info', duration = 5000) {
        if (!this.container) return;
        
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
        
        this.container.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                this.closeNotification(notification);
            }, duration);
        }
    },
    
    closeNotification(element) {
        let notification;
        if (element.tagName === 'BUTTON') {
            notification = element.closest('.notification');
        } else {
            notification = element;
        }
        
        if (notification) {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    },
    
    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },
    
    success(title, message, duration) {
        this.showNotification(title, message, 'success', duration);
    },
    
    error(title, message, duration) {
        this.showNotification(title, message, 'error', duration);
    },
    
    warning(title, message, duration) {
        this.showNotification(title, message, 'warning', duration);
    },
    
    info(title, message, duration) {
        this.showNotification(title, message, 'info', duration);
    }
};

// ========== 主题管理器 ==========
const ThemeManager = {
    themes: ['default', 'dark', 'ocean', 'green', 'sunset', 'cyber'],
    themeNames: {
        'default': '暗夜紫',
        'dark': '深色模式',
        'ocean': '深海蓝',
        'green': '清新绿',
        'sunset': '暮色橙',
        'cyber': '科技感霓虹'
    },
    
    getCurrentTheme() {
        return localStorage.getItem('currentTheme') || 'default';
    },
    
    setTheme(themeName) {
        this.themes.forEach(theme => {
            document.body.classList.remove(`theme-${theme}`);
        });
        
        if (themeName !== 'default') {
            document.body.classList.add(`theme-${themeName}`);
        }
        
        localStorage.setItem('currentTheme', themeName);
        this.updateThemeRadioButtons(themeName);
        console.log(`主题已切换为: ${this.themeNames[themeName]}`);
    },
    
    updateThemeRadioButtons(themeName) {
        const radioButton = document.querySelector(`input[name="theme"][value="${themeName}"]`);
        if (radioButton) radioButton.checked = true;
    },
    
    initTheme() {
        let currentTheme = this.getCurrentTheme();
        
        if (currentTheme === 'default') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) currentTheme = 'dark';
        }
        
        this.setTheme(currentTheme);
        
        document.querySelectorAll('input[name="theme"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.setTheme(e.target.value);
            });
        });
        
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (this.getCurrentTheme() === 'default') {
                this.setTheme(e.matches ? 'dark' : 'default');
            }
        });
    },
    
    toggleNext() {
        const themes = this.themes;
        const current = this.getCurrentTheme();
        const currentIndex = themes.indexOf(current);
        const nextIndex = (currentIndex + 1) % themes.length;
        this.setTheme(themes[nextIndex]);
    },
    
    reset() {
        this.setTheme('default');
    }
};

// ========== 导出到全局 ==========
window.currentConfig = currentConfig;
window.eventCategoriesCache = eventCategoriesCache;
window.sessionCheckInterval = sessionCheckInterval;
window.activityRefreshInterval = activityRefreshInterval;
window.lastActivityTime = lastActivityTime;
window.healthUpdateInterval = healthUpdateInterval;
window.autoRefreshInterval = autoRefreshInterval;
window.sidebarOpen = sidebarOpen;
window.sidebarCollapsed = sidebarCollapsed;
window.lastHistoryIndex = lastHistoryIndex;
window._historySearchTimer = _historySearchTimer;
window.historyKeyword = historyKeyword;
window.historyCurrentPage = historyCurrentPage;
window.historyPageSize = historyPageSize;
window.historyTotal = historyTotal;
window.historyDateFilter = historyDateFilter;
window.CONSTANTS = CONSTANTS;
window.DEFAULT_REFRESH_INTERVAL = DEFAULT_REFRESH_INTERVAL;
window.NotificationManager = NotificationManager;
window.ThemeManager = ThemeManager;
