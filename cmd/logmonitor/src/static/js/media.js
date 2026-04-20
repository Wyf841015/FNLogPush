// ========== 影视监控模块 ==========
// 影视监控前端JS模块

var mediaMonitor = {
    config: {
        enabled: false,
        db_path: '/usr/local/apps/@appdata/trim.media/database/trimmedia.db',
        activity_db_path: '/usr/local/apps/@appdata/trim.media/database/trimactivity.db',
        poll_interval: 10,
        monitor_events: []
    },
    status: {
        running: false,
        db_available: false,
        activity_db_available: false
    }
};

// 加载配置
async function loadMediaConfig() {
    try {
        var resp = await fetch('/api/media/config');
        if (resp.ok) {
            var data = await resp.json();
            if (data.data) {
                mediaMonitor.config = { ...mediaMonitor.config, ...data.data };
                return true;
            }
        }
    } catch (e) { console.error('Load media config failed:', e); }
    return false;
}

// 加载状态
async function loadMediaStatus() {
    try {
        var resp = await fetch('/api/media/status');
        if (resp.ok) {
            var data = await resp.json();
            if (data.data) {
                mediaMonitor.status = data.data;
                return data.data;
            }
        }
    } catch (e) { console.error('Load media status failed:', e); }
    return null;
}

// 保存配置
async function saveMediaConfig(config) {
    try {
        var resp = await fetch('/api/media/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return resp.ok;
    } catch (e) { console.error('Save media config failed:', e); return false; }
}

// 切换启用状态
async function toggleMediaMonitor(enabled) {
    try {
        var resp = await fetch('/api/media/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: enabled })
        });
        return resp.ok;
    } catch (e) { console.error('Toggle media monitor failed:', e); return false; }
}

// 获取事件列表
async function getMediaEvents(limit) {
    try {
        var resp = await fetch('/api/media/events?limit=' + (limit || 50));
        if (resp.ok) {
            var data = await resp.json();
            return data.data || [];
        }
    } catch (e) { console.error('Get media events failed:', e); }
    return [];
}

// 事件类型信息
function getMediaEventTypeInfo(type) {
    var types = {
        'MEDIA_RESOURCE_ADDED': { label: '资源入库', color: 'success', icon: 'fa-plus-circle' },
        'MEDIA_SCRAPE_SUCCESS': { label: '刮削完成', color: 'primary', icon: 'fa-check-circle' },
        'MEDIA_LOGIN_SUCCESS': { label: '用户登录', color: 'info', icon: 'fa-sign-in-alt' },
        'MEDIA_LOGOUT': { label: '用户登出', color: 'warning', icon: 'fa-sign-out-alt' }
    };
    return types[type] || { label: type, color: 'secondary', icon: 'fa-circle' };
}

// 格式化事件为推送消息
function formatMediaEventMessage(event) {
    var typeInfo = getMediaEventTypeInfo(event.type);
    var title = event.title || '未知';
    var itemType = event.item_type || '';
    var year = event.year ? ' (' + event.year + ')' : '';
    
    var messages = {
        'MEDIA_RESOURCE_ADDED': '🎬 新增影视资源\n' + title + '\n类型: ' + itemType + year + '\n时间: ' + (event.datetime || event.time),
        'MEDIA_SCRAPE_SUCCESS': '✅ 刮削完成\n' + title + '\n类型: ' + itemType + year + '\n时间: ' + (event.datetime || event.time),
        'MEDIA_LOGIN_SUCCESS': '🔵 用户登录\n' + event.username + '\nIP: ' + event.ip + '\n时间: ' + (event.datetime || event.time),
        'MEDIA_LOGOUT': '🟡 用户登出\n' + event.username + '\n时间: ' + (event.datetime || event.time)
    };
    return messages[event.type] || event.type + ': ' + title;
}
