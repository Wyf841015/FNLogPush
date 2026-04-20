// Photo monitor JS module

var photoConfig = {
    enabled: false,
    db_path: '/usr/local/apps/@appdata/trim.photos/db/photo.db',
    poll_interval: 10,
    monitor_events: []
};

async function initPhotoSettings() {
    await loadPhotoConfig();
    await loadPhotoStatus();
    await refreshPhotoEvents();
    setInterval(refreshPhotoStatus, 30000);
}

async function loadPhotoConfig() {
    try {
        var resp = await fetch('/api/photo/config');
        if (resp.ok) {
            var data = await resp.json();
            if (data.data) {
                photoConfig = Object.assign(photoConfig, data.data);
                updatePhotoUI();
            }
        }
    } catch (e) { console.error('Load photo config failed:', e); }
}

function updatePhotoUI() {
    document.getElementById('photoMonitorEnabled').checked = photoConfig.enabled;
    document.getElementById('photoDbPathInput').value = photoConfig.db_path || '';
    document.getElementById('photoPollInterval').value = photoConfig.poll_interval || 10;
    var events = photoConfig.monitor_events || [];
    document.getElementById('photoEventShareCreated').checked = events.includes('PHOTO_SHARE_CREATED');
    document.getElementById('photoEventShareExpired').checked = events.includes('PHOTO_SHARE_EXPIRED');
    document.getElementById('photoEventDeviceRegistered').checked = events.includes('PHOTO_DEVICE_REGISTERED');
    document.getElementById('photoEventFaceRecognition').checked = events.includes('FACE_RECOGNITION_UPDATED');
}

async function loadPhotoStatus() {
    try {
        var resp = await fetch('/api/photo/status');
        if (resp.ok) {
            var data = await resp.json();
            if (data.data) updatePhotoStatusUI(data.data);
        }
    } catch (e) { console.error('Load photo status failed:', e); }
}

function updatePhotoStatusUI(status) {
    var dbPathEl = document.getElementById('photoDbPath');
    if (dbPathEl) dbPathEl.textContent = status.db_path || '-';
    var dbInd = document.getElementById('photoDbIndicator');
    if (dbInd) dbInd.className = 'status-indicator ' + (status.db_available ? 'online' : 'offline');
}

async function refreshPhotoStatus() { await loadPhotoStatus(); }

async function togglePhotoMonitor() {
    var enabled = document.getElementById('photoMonitorEnabled').checked;
    try {
        var resp = await fetch('/api/photo/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: enabled })
        });
        if (resp.ok) {
            photoConfig.enabled = enabled;
            showToast(enabled ? 'Photo monitor enabled' : 'Photo monitor disabled', 'success');
            await refreshPhotoStatus();
        }
    } catch (e) { console.error('Toggle failed:', e); showToast('Operation failed', 'error'); }
}

async function savePhotoSettings() {
    var events = [];
    if (document.getElementById('photoEventShareCreated').checked) events.push('PHOTO_SHARE_CREATED');
    if (document.getElementById('photoEventShareExpired').checked) events.push('PHOTO_SHARE_EXPIRED');
    if (document.getElementById('photoEventDeviceRegistered').checked) events.push('PHOTO_DEVICE_REGISTERED');
    if (document.getElementById('photoEventFaceRecognition').checked) events.push('FACE_RECOGNITION_UPDATED');
    var newConfig = {
        enabled: photoConfig.enabled,
        db_path: document.getElementById('photoDbPathInput').value,
        poll_interval: parseInt(document.getElementById('photoPollInterval').value) || 10,
        monitor_events: events
    };
    try {
        var resp = await fetch('/api/photo/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newConfig)
        });
        if (resp.ok) {
            photoConfig = newConfig;
            showToast('Settings saved', 'success');
        } else { showToast('Save failed', 'error'); }
    } catch (e) { console.error('Save failed:', e); showToast('Save failed', 'error'); }
}

function resetPhotoSettings() {
    document.getElementById('photoDbPathInput').value = '/usr/local/apps/@appdata/trim.photos/db/photo.db';
    document.getElementById('photoPollInterval').value = 10;
    document.getElementById('photoEventShareCreated').checked = true;
    document.getElementById('photoEventShareExpired').checked = false;
    document.getElementById('photoEventDeviceRegistered').checked = false;
    document.getElementById('photoEventFaceRecognition').checked = false;
    showToast('Reset to defaults', 'info');
}

async function refreshPhotoEvents() {
    try {
        var resp = await fetch('/api/photo/events');
        if (resp.ok) {
            var data = await resp.json();
            updatePhotoEventsTable(data.data || []);
        }
    } catch (e) { console.error('Load events failed:', e); }
}

function getPhotoEventTypeInfo(type) {
    var types = {
        'PHOTO_SHARE_CREATED': { label: 'Share Created', color: 'success' },
        'PHOTO_SHARE_EXPIRED': { label: 'Share Expired', color: 'danger' },
        'PHOTO_DEVICE_REGISTERED': { label: 'Device Registered', color: 'info' },
        'FACE_RECOGNITION_UPDATED': { label: 'Face Recognition', color: 'warning' }
    };
    return types[type] || { label: type, color: 'secondary' };
}

function updatePhotoEventsTable(events) {
    var tbody = document.getElementById('photoEventsTable');
    if (!tbody) return;
    if (events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">No events</td></tr>';
        return;
    }
    var html = '';
    for (var i = 0; i < events.length; i++) {
        var event = events[i];
        var typeInfo = getPhotoEventTypeInfo(event.type);
        html += '<tr><td><small>' + (event.datetime || '-') + '</small></td>';
        html += '<td><span class="badge bg-' + typeInfo.color + '">' + typeInfo.label + '</span></td>';
        html += '<td>' + (event.title || event.device_name || '-') + '</td>';
        html += '<td><small class="text-muted">' + (event.link || event.device_type || '') + '</small></td></tr>';
    }
    tbody.innerHTML = html;
}
