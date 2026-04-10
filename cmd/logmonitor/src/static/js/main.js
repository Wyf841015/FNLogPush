// ========== main.js - 入口文件 ==========
// 此文件为入口文件，负责初始化和模块加载
// 具体功能已拆分到各模块文件中

// ========== 全局状态 ==========
let currentConfig = {};

// ========== 初始化 ==========

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== DOMContentLoaded 事件触发 ===');
    
    // 动态设置版权年份
    const copyrightYear = document.getElementById('copyright-year');
    if (copyrightYear) {
        copyrightYear.textContent = new Date().getFullYear();
    }

    // 启动session定时检查
    if (typeof startSessionCheck === 'function') {
        startSessionCheck();
    }

    // 检查会话状态并加载用户信息
    if (typeof checkSession === 'function') {
        checkSession();
    }

    // 初始化主题
    if (typeof ThemeManager !== 'undefined' && ThemeManager.initTheme) {
        ThemeManager.initTheme();
    }

    // 初始化侧边栏
    if (typeof initSidebar === 'function') {
        initSidebar();
    }

    // ========== WebSocket 实时推送初始化 ==========
    if (typeof initWebSocket === 'function') {
        initWebSocket();
    } else if (typeof wsManager !== 'undefined' && wsManager.init) {
        wsManager.init();
    }

    // ========== 加载初始状态 ==========
    loadStatus();
    
    // 初始化自动刷新
    if (typeof initAutoRefresh === 'function') {
        initAutoRefresh();
    }
    
    // 初始化历史记录日期筛选
    if (typeof initHistoryDateFilter === 'function') {
        initHistoryDateFilter();
    }

    // ========== 欢迎通知 ==========
    setTimeout(() => {
        if (typeof NotificationManager !== 'undefined' && NotificationManager.success) {
            NotificationManager.success('欢迎使用', '日志监控推送系统已成功加载');
        }
    }, 1000);

    // ========== 加载聚合统计 ==========
    if (typeof loadAggStats === 'function') {
        loadAggStats();
    }
});

// ========== 状态加载（整合函数） ==========

/**
 * 加载状态信息
 */
function loadStatus() {
    return Promise.all([
        apiFetch('/api/status').then(r => r.json()).catch(() => ({ error: '请求失败' })),
        apiFetch('/api/backup/status').then(r => r.json()).catch(() => ({ db_available: false }))
    ])
        .then(([data, backupData]) => {
            if (data.error) {
                const statusEl = document.getElementById('monitor-status');
                if (statusEl) {
                    statusEl.className = 'badge badge-offline';
                    statusEl.textContent = '异常';
                }
                return;
            }

            // 更新监控状态
            const statusBadge = document.getElementById('monitor-status');
            if (statusBadge) {
                statusBadge.className = data.running ? 'badge badge-online' : 'badge badge-offline';
                statusBadge.textContent = data.running ? '运行中' : '已停止';
            }

            // 更新基本信息
            const updateText = (id, value) => {
                const el = document.getElementById(id);
                if (el) el.textContent = value;
            };
            
            updateText('last-id', data.last_id);
            updateText('history-count', (data.history_count || 0) + ' 条');
            updateText('check-interval', (data.config?.check_interval || 5) + ' 秒');

            // 更新最后日志ID的相对时间
            const lastIdRelEl = document.getElementById('last-id-relative');
            if (lastIdRelEl && data.last_history_timestamp && data.last_history_timestamp !== '-') {
                const time = new Date(data.last_history_timestamp);
                lastIdRelEl.textContent = time.toLocaleTimeString('zh-CN', { hour12: false }) + ' · ' + formatRelativeTime(data.last_history_timestamp);
            }

            // 更新数据库状态
            const dbIndicator = document.getElementById('db-status-indicator');
            if (dbIndicator) {
                const dbStatus = data.db_connection_status || '未连接';
                dbIndicator.className = dbStatus === '已连接' ? 'badge badge-online' : 'badge bg-secondary';
                dbIndicator.textContent = dbStatus;
            }

            // 更新备份数据库状态
            const backupIndicator = document.getElementById('backup-db-status-indicator');
            if (backupIndicator) {
                const backupStatus = backupData.db_available ? '已连接' : '未连接';
                backupIndicator.className = backupData.db_available ? 'badge badge-online' : 'badge bg-secondary';
                backupIndicator.textContent = backupStatus;
            }

            // 更新DND状态
            const dndIndicator = document.getElementById('dnd-status');
            if (dndIndicator && data.dnd) {
                dndIndicator.textContent = data.dnd.enabled ? `已启用 (${data.dnd.start_time}-${data.dnd.end_time})` : '已禁用';
            }
            
            // 保存配置
            currentConfig = data.config || {};
        });
}

// ========== 导出到全局 ==========
window.currentConfig = currentConfig;
window.loadStatus = loadStatus;
