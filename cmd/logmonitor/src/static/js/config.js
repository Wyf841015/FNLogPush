// ========== config.js - 配置管理模块 ==========

// ========== 监控控制 ==========

function controlMonitor(action) {
    apiFetch('/api/control', {
        credentials: 'same-origin',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            NotificationManager.success('操作成功', data.message || '操作成功！');
            loadStatus();
        } else {
            NotificationManager.error('操作失败', data.error || '操作失败！');
        }
    });
}

// ========== 配置保存函数 ==========

async function saveBasicConfig() {
    const event_ids = Array.from(document.querySelectorAll('input[name="event_ids"]:checked')).map(cb => cb.value);
    const selected_levels = Array.from(document.querySelectorAll('input[name="levels"]:checked')).map(cb => cb.value);
    const check_interval = parseInt(document.getElementById('check_interval')?.value) || 5;
    const history_size = parseInt(document.getElementById('history_size')?.value) || 100;
    const database_path = document.getElementById('database_path')?.value || '';
    
    const config = {
        event_ids,
        selected_levels,
        check_interval,
        history_size,
        database_path
    };
    
    try {
        const response = await apiFetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        if (data.success) {
            NotificationManager.success('保存成功', '基础配置已保存');
        } else {
            NotificationManager.error('保存失败', data.error || '保存失败');
        }
    } catch (e) {
        NotificationManager.error('保存失败', e.message);
    }
}

async function savePushConfig() {
    const push_channels = {};
    document.querySelectorAll('.push-channel-enabled').forEach(cb => {
        push_channels[cb.dataset.channel] = cb.checked;
    });
    
    const channelConfigs = {};
    document.querySelectorAll('.channel-config').forEach(input => {
        channelConfigs[input.dataset.channel] = channelConfigs[input.dataset.channel] || {};
        channelConfigs[input.dataset.channel][input.dataset.key] = input.value;
    });
    
    const config = {
        push_channels,
        ...channelConfigs
    };
    
    try {
        const response = await apiFetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        if (data.success) {
            NotificationManager.success('保存成功', '推送配置已保存');
        } else {
            NotificationManager.error('保存失败', data.error || '保存失败');
        }
    } catch (e) {
        NotificationManager.error('保存失败', e.message);
    }
}

async function saveFilterConfig() {
    const selected_events = Array.from(document.querySelectorAll('input[name="selected_events"]:checked')).map(cb => cb.value);
    const selected_levels = Array.from(document.querySelectorAll('input[name="selected_levels"]:checked')).map(cb => cb.value);
    
    const config = { selected_events, selected_levels };
    
    try {
        const response = await apiFetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        if (data.success) {
            NotificationManager.success('保存成功', '过滤配置已保存');
        } else {
            NotificationManager.error('保存失败', data.error || '保存失败');
        }
    } catch (e) {
        NotificationManager.error('保存失败', e.message);
    }
}

async function saveThemeConfig() {
    const theme = document.querySelector('input[name="theme"]:checked')?.value || 'default';
    
    const config = { theme };
    
    try {
        const response = await apiFetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        if (data.success) {
            NotificationManager.success('保存成功', '主题配置已保存');
        } else {
            NotificationManager.error('保存失败', data.error || '保存失败');
        }
    } catch (e) {
        NotificationManager.error('保存失败', e.message);
    }
}

async function saveBackupConfig() {
    const backup_db_path = document.getElementById('backup_db_path')?.value || '';
    const backup_check_interval = parseInt(document.getElementById('backup_check_interval')?.value) || 60;
    
    const config = { backup_db_path, backup_check_interval };
    
    try {
        const response = await apiFetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        if (data.success) {
            NotificationManager.success('保存成功', '备份配置已保存');
        } else {
            NotificationManager.error('保存失败', data.error || '保存失败');
        }
    } catch (e) {
        NotificationManager.error('保存失败', e.message);
    }
}

// ========== 测试函数 ==========

async function testWebhook() {
    const webhookUrl = document.getElementById('webhook_url')?.value;
    if (!webhookUrl) {
        NotificationManager.warning('测试失败', '请先配置 Webhook URL');
        return;
    }
    
    NotificationManager.info('测试中', '正在发送测试消息...');
    
    try {
        const response = await apiFetch('/api/test/webhook', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ webhook_url: webhookUrl })
        });
        const data = await response.json();
        if (data.success) {
            NotificationManager.success('测试成功', 'Webhook 测试消息发送成功');
        } else {
            NotificationManager.error('测试失败', data.error || '发送失败');
        }
    } catch (e) {
        NotificationManager.error('测试失败', e.message);
    }
}

async function testBackupDbConnection() {
    const backupDbPath = document.getElementById('backup_db_path')?.value;
    if (!backupDbPath) {
        NotificationManager.warning('测试失败', '请先配置备份数据库路径');
        return;
    }
    
    NotificationManager.info('测试中', '正在连接备份数据库...');
    
    try {
        const response = await apiFetch('/api/backup/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: backupDbPath })
        });
        const data = await response.json();
        if (data.success) {
            NotificationManager.success('连接成功', `数据库连接成功，包含 ${data.tables?.length || 0} 个表`);
        } else {
            NotificationManager.error('连接失败', data.error || '连接失败');
        }
    } catch (e) {
        NotificationManager.error('连接失败', e.message);
    }
}

async function checkDatabaseFull() {
    const checkbox = document.getElementById('checkDatabaseFull');
    if (checkbox?.checked) {
        NotificationManager.warning('数据库告警', '⚠️ 检测到数据库已满！建议清理历史记录。');
    }
}

// ========== 分类选择 ==========

function selectAllInCategory(category) {
    document.querySelectorAll(`input[name="event_ids"][data-category="${category}"]`).forEach(cb => cb.checked = true);
}

function deselectAllInCategory(category) {
    document.querySelectorAll(`input[name="event_ids"][data-category="${category}"]`).forEach(cb => cb.checked = false);
}

// ========== 导出 ==========
window.controlMonitor = controlMonitor;
window.saveBasicConfig = saveBasicConfig;
window.savePushConfig = savePushConfig;
window.saveFilterConfig = saveFilterConfig;
window.saveThemeConfig = saveThemeConfig;
window.saveBackupConfig = saveBackupConfig;
window.testWebhook = testWebhook;
window.testBackupDbConnection = testBackupDbConnection;
window.checkDatabaseFull = checkDatabaseFull;
window.selectAllInCategory = selectAllInCategory;
window.deselectAllInCategory = deselectAllInCategory;
