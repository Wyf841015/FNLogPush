// ========== stats.js - 统计模块 ==========

// ========== 告警聚合统计 ==========

function loadAggStats() {
    const container = document.getElementById('agg-stats-content');
    if (!container) return;
    
    container.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>';
    
    apiFetch('/api/agg/stats')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.stats) {
                const stats = data.stats;
                container.innerHTML = `
                    <div class="row">
                        <div class="col-md-4 mb-3">
                            <div class="card text-center">
                                <div class="card-body">
                                    <h3 class="text-primary">${stats.total_log_events || 0}</h3>
                                    <p class="text-muted mb-0">总日志事件</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <div class="card text-center">
                                <div class="card-body">
                                    <h3 class="text-success">${stats.total_pushed || 0}</h3>
                                    <p class="text-muted mb-0">总推送次数</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4 mb-3">
                            <div class="card text-center">
                                <div class="card-body">
                                    <h3 class="text-warning">${stats.total_suppressed || 0}</h3>
                                    <p class="text-muted mb-0">被压制次数</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    ${stats.suppression_rate ? `
                        <div class="alert alert-info">
                            <i class="fas fa-chart-line me-2"></i>
                            压制率: ${(stats.suppression_rate * 100).toFixed(1)}%
                        </div>
                    ` : ''}
                `;
            } else {
                container.innerHTML = '<div class="alert alert-info">暂无统计数据</div>';
            }
        })
        .catch(error => {
            container.innerHTML = `<div class="alert alert-danger">加载失败: ${error.message}</div>`;
        });
}

// ========== 自动刷新 ==========

let autoRefreshInterval = null;
const DEFAULT_REFRESH_INTERVAL = 10000;

function toggleAutoRefresh(enabled) {
    if (enabled) {
        startAutoRefresh();
    } else {
        stopAutoRefresh();
    }
}

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    
    autoRefreshInterval = setInterval(() => {
        loadStatus();
        loadHistory();
    }, DEFAULT_REFRESH_INTERVAL);
    
    console.log('自动刷新已启动');
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
    console.log('自动刷新已停止');
}

function initAutoRefresh() {
    // 可根据配置决定是否自动开启
    // startAutoRefresh();
}

// ========== 导出 ==========
window.loadAggStats = loadAggStats;
window.toggleAutoRefresh = toggleAutoRefresh;
window.startAutoRefresh = startAutoRefresh;
window.stopAutoRefresh = stopAutoRefresh;
window.initAutoRefresh = initAutoRefresh;
