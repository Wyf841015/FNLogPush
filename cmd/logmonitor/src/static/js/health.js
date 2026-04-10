// ========== health.js - 健康状态监控模块 ==========

// ========== 健康状态轮询 ==========
let healthUpdateInterval = null;

/**
 * 加载健康状态
 */
function loadHealthStatus() {
    const content = document.getElementById('health-status-content');
    if (!content) return;
    
    content.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin me-2"></i>检查中...</div>';
    
    apiFetch('/api/health')
        .then(response => response.json())
        .then(data => {
            updateHealthStatusData(data);
        })
        .catch(error => {
            content.innerHTML = `<div class="alert alert-danger">加载失败: ${error.message}</div>`;
        });
}

/**
 * 更新健康状态数据
 * @param {Object} data - 健康状态数据
 */
function updateHealthStatusData(data) {
    const content = document.getElementById('health-status-content');
    if (!content) return;
    
    if (data.status === 'healthy') {
        let html = `
            <div class="health-alert-success">
                <h6 class="mb-3">系统健康状态: <span class="badge health-badge-success"><i class="fas fa-check-circle me-1"></i>健康</span></h6>
                <div class="mb-2">
                    <button class="btn btn-sm btn-outline-secondary" onclick="startHealthUpdate()">
                        <i class="fas fa-play me-1"></i>开始实时更新
                    </button>
                    <button class="btn btn-sm btn-outline-secondary ms-2" onclick="stopHealthUpdate()">
                        <i class="fas fa-stop me-1"></i>停止实时更新
                    </button>
                </div>
        `;
        
        // 系统信息
        if (data.system) {
            html += `
                <div class="card mb-3">
                    <div class="card-header health-card-system">系统信息</div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">系统: ${data.system.system} ${data.system.release}</li>
                            <li class="list-group-item">Python版本: ${data.system.python_version}</li>
                            <li class="list-group-item">机器类型: ${data.system.machine}</li>
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // CPU信息
        if (data.cpu) {
            html += `
                <div class="card mb-3">
                    <div class="card-header health-card-cpu">CPU信息</div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">物理核心: ${data.cpu.physical_cores}</li>
                            <li class="list-group-item">总核心: ${data.cpu.total_cores}</li>
                            <li class="list-group-item cpu-usage">CPU使用率: <span id="cpu-usage">${data.cpu.cpu_percent}</span>%</li>
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // 内存信息
        if (data.memory) {
            const totalMem = (data.memory.total / 1024 / 1024 / 1024).toFixed(2);
            const usedMem = (data.memory.used / 1024 / 1024 / 1024).toFixed(2);
            const memPercent = ((data.memory.used / data.memory.total) * 100).toFixed(1);
            
            html += `
                <div class="card mb-3">
                    <div class="card-header health-card-memory">内存信息</div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">总内存: ${totalMem} GB</li>
                            <li class="list-group-item">已用内存: ${usedMem} GB (${memPercent}%)</li>
                            <li class="list-group-item memory-usage">内存使用率: <span id="memory-usage">${memPercent}</span>%</li>
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // 磁盘信息
        if (data.disk) {
            const diskTotal = (data.disk.total / 1024 / 1024 / 1024).toFixed(2);
            const diskUsed = (data.disk.used / 1024 / 1024 / 1024).toFixed(2);
            const diskPercent = ((data.disk.used / data.disk.total) * 100).toFixed(1);
            
            html += `
                <div class="card mb-3">
                    <div class="card-header health-card-disk">磁盘信息</div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">总磁盘: ${diskTotal} GB</li>
                            <li class="list-group-item">已用磁盘: ${diskUsed} GB (${diskPercent}%)</li>
                        </ul>
                    </div>
                </div>
            `;
        }
        
        // 数据库信息
        if (data.database) {
            html += `
                <div class="card mb-3">
                    <div class="card-header health-card-database">数据库</div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">数据库: ${data.database.message || '已连接'}</li>
                            ${data.database.size ? `<li class="list-group-item">数据库大小: ${data.database.size}</li>` : ''}
                        </ul>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        content.innerHTML = html;
        
        // 动态更新使用率数字
        if (data.cpu && document.getElementById('cpu-usage')) {
            animateNumber(document.getElementById('cpu-usage'), data.cpu.cpu_percent + '%');
        }
        if (data.memory && document.getElementById('memory-usage')) {
            animateNumber(document.getElementById('memory-usage'), memPercent + '%');
        }
        
    } else {
        // 不健康状态
        content.innerHTML = `
            <div class="health-alert-error">
                <h6><i class="fas fa-exclamation-triangle me-2"></i>系统状态异常</h6>
                <p>${data.message || '请检查系统配置'}</p>
            </div>
        `;
    }
}

/**
 * 更新健康状态（轮询）
 */
function updateHealthStatus() {
    apiFetch('/api/health')
        .then(response => response.json())
        .then(data => {
            updateHealthStatusData(data);
        })
        .catch(error => {
            console.error('更新健康状态失败:', error);
        });
}

/**
 * 开始实时更新
 */
function startHealthUpdate() {
    if (healthUpdateInterval) {
        clearInterval(healthUpdateInterval);
    }
    
    // 设置WebSocket健康状态回调
    if (wsManager && wsManager.onHealthStatus === null) {
        wsManager.onHealthStatus = (data) => {
            updateHealthStatusData(data);
        };
        console.log('已注册WebSocket健康状态监听器');
    }
    
    // 保留备用轮询（如果WebSocket断开时自动切换）
    healthUpdateInterval = setInterval(() => {
        if (!wsManager || !wsManager.connected) {
            updateHealthStatus();
        }
    }, (window.CONSTANTS?.REFRESH_INTERVAL?.HEALTH) || 15000);
    
    NotificationManager.info('实时更新', '已开始实时更新系统状态（WebSocket推送）');
}

/**
 * 停止实时更新
 */
function stopHealthUpdate() {
    if (healthUpdateInterval) {
        clearInterval(healthUpdateInterval);
        healthUpdateInterval = null;
    }
    NotificationManager.info('实时更新', '已停止实时更新系统状态');
}

// ========== 导出到全局 ==========
window.healthUpdateInterval = healthUpdateInterval;
window.loadHealthStatus = loadHealthStatus;
window.updateHealthStatusData = updateHealthStatusData;
window.updateHealthStatus = updateHealthStatus;
window.startHealthUpdate = startHealthUpdate;
window.stopHealthUpdate = stopHealthUpdate;
