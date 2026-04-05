// ========== 模块已分离 ==========
// api.js - API 请求模块
// websocket.js - WebSocket 管理模块
// components.js - UI 组件模块

// 统一Fetch函数（使用 api.js 中的实现）
// 此文件中的 apiFetch 已由 api.js 提供

// ========== Session 超时管理（5分钟无操作退出） ==========
let sessionCheckInterval = null;
let activityRefreshInterval = null;
let lastActivityTime = Date.now();

// 刷新活动时间
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

// 检测用户活动
function setupActivityDetection() {
    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    
    activityEvents.forEach(event => {
        document.addEventListener(event, () => {
            lastActivityTime = Date.now();
        }, { passive: true });
    });
}

// 启动定时检查（每分钟检查一次，5分钟无操作则退出）
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

// 动态设置版权年份
document.getElementById('copyright-year').textContent = new Date().getFullYear();

// 通知管理功能
const NotificationManager = {
    container: document.getElementById('notification-container'),
    
    // 显示通知
    showNotification(title, message, type = 'info', duration = 5000) {
        if (!this.container) return;
        
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        // 设置通知内容
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
        
        // 添加到容器
        this.container.appendChild(notification);
        
        // 自动关闭
        if (duration > 0) {
            setTimeout(() => {
                this.closeNotification(notification);
            }, duration);
        }
    },
    
    // 关闭通知
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
    
    // 获取当前时间
    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },
    
    // 显示成功通知
    success(title, message, duration) {
        this.showNotification(title, message, 'success', duration);
    },
    
    // 显示错误通知
    error(title, message, duration) {
        this.showNotification(title, message, 'error', duration);
    },
    
    // 显示警告通知
    warning(title, message, duration) {
        this.showNotification(title, message, 'warning', duration);
    },
    
    // 显示信息通知
    info(title, message, duration) {
        this.showNotification(title, message, 'info', duration);
    }
};

// 测试通知功能
function testNotification() {
    NotificationManager.success('测试成功', '这是一条成功通知');
    setTimeout(() => {
        NotificationManager.info('系统信息', '这是一条信息通知');
    }, 1000);
    setTimeout(() => {
        NotificationManager.warning('警告信息', '这是一条警告通知');
    }, 2000);
    setTimeout(() => {
        NotificationManager.error('错误信息', '这是一条错误通知');
    }, 3000);
}

// 健康检查更新定时器
let healthUpdateInterval = null;

// 加载系统健康状态
function loadHealthStatus() {
    const content = document.getElementById('health-status-content');
    content.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin me-2"></i>检查中...</div>';
    
    apiFetch('/api/health')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'healthy') {
                let html = `
                    <div class="alert alert-success">
                        <h6 class="mb-3">系统健康状态: <span class="badge bg-success" aria-label="系统健康状态：健康"><i class="fas fa-check-circle me-1" aria-hidden="true"></i>健康</span></h6>
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
                            <div class="card-header bg-info text-white">系统信息</div>
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
                            <div class="card-header bg-primary text-white">CPU信息</div>
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
                    const freeMem = (data.memory.free / 1024 / 1024 / 1024).toFixed(2);
                    
                    html += `
                        <div class="card mb-3">
                            <div class="card-header bg-success text-white">内存信息</div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item">总内存: ${totalMem} GB</li>
                                    <li class="list-group-item memory-usage">已用内存: <span id="memory-usage">${usedMem}</span> GB (<span id="memory-percent">${data.memory.percent}</span>%)</li>
                                    <li class="list-group-item">可用内存: ${freeMem} GB</li>
                                </ul>
                            </div>
                        </div>
                    `;
                }
                
                // 磁盘信息
                if (data.disk) {
                    const totalDisk = (data.disk.total / 1024 / 1024 / 1024).toFixed(2);
                    const usedDisk = (data.disk.used / 1024 / 1024 / 1024).toFixed(2);
                    const freeDisk = (data.disk.free / 1024 / 1024 / 1024).toFixed(2);
                    
                    html += `
                        <div class="card mb-3">
                            <div class="card-header bg-warning text-dark">磁盘信息</div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item">总空间: ${totalDisk} GB</li>
                                    <li class="list-group-item">已用空间: ${usedDisk} GB (${data.disk.percent}%)</li>
                                    <li class="list-group-item">可用空间: ${freeDisk} GB</li>
                                </ul>
                            </div>
                        </div>
                    `;
                }
                
                // 进程信息
                if (data.process) {
                    html += `
                        <div class="card mb-3">
                            <div class="card-header bg-secondary text-white">进程信息</div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item">进程ID: ${data.process.pid}</li>
                                    <li class="list-group-item">进程名称: ${data.process.name}</li>
                                    <li class="list-group-item process-memory">内存使用率: <span id="process-memory">${data.process.memory_percent.toFixed(2)}</span>%</li>
                                    <li class="list-group-item process-cpu">CPU使用率: <span id="process-cpu">${data.process.cpu_percent.toFixed(2)}</span>%</li>
                                </ul>
                            </div>
                        </div>
                    `;
                }
                
                html += '</div>';
                content.innerHTML = html;
                NotificationManager.success('健康检查', '系统状态正常');
            } else {
                content.innerHTML = `
                    <div class="alert alert-danger">
                        <h6>系统健康状态: <span class="badge bg-danger" aria-label="系统健康状态：异常"><i class="fas fa-exclamation-circle me-1" aria-hidden="true"></i>异常</span></h6>
                        <p>错误信息: ${data.error}</p>
                    </div>
                `;
                NotificationManager.error('健康检查', '系统状态异常');
            }
        })
        .catch(error => {
            console.error('健康检查失败:', error);
            content.innerHTML = `
                <div class="alert alert-danger">
                    <h6>健康检查失败</h6>
                    <p>无法连接到健康检查服务</p>
                </div>
            `;
            NotificationManager.error('健康检查', '无法连接到健康检查服务');
        });
}

// 实时更新健康状态
function updateHealthStatus() {
    apiFetch('/api/health')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'healthy') {
                // 更新CPU使用率
                if (data.cpu) {
                    const cpuUsageElement = document.getElementById('cpu-usage');
                    if (cpuUsageElement) {
                        cpuUsageElement.textContent = data.cpu.cpu_percent;
                    }
                }
                
                // 更新内存使用率
                if (data.memory) {
                    const memoryUsageElement = document.getElementById('memory-usage');
                    const memoryPercentElement = document.getElementById('memory-percent');
                    if (memoryUsageElement && memoryPercentElement) {
                        const usedMem = (data.memory.used / 1024 / 1024 / 1024).toFixed(2);
                        memoryUsageElement.textContent = usedMem;
                        memoryPercentElement.textContent = data.memory.percent;
                    }
                }
                
                // 更新进程使用率
                if (data.process) {
                    const processMemoryElement = document.getElementById('process-memory');
                    const processCpuElement = document.getElementById('process-cpu');
                    if (processMemoryElement && processCpuElement) {
                        processMemoryElement.textContent = data.process.memory_percent.toFixed(2);
                        processCpuElement.textContent = data.process.cpu_percent.toFixed(2);
                    }
                }
            }
        })
        .catch(error => {
            console.error('更新健康状态失败:', error);
        });
}

// 开始实时更新
function startHealthUpdate() {
    if (healthUpdateInterval) {
        clearInterval(healthUpdateInterval);
    }
    healthUpdateInterval = setInterval(updateHealthStatus, 15000); // 每15秒更新一次
    NotificationManager.info('实时更新', '已开始实时更新系统状态');
}

// 停止实时更新
function stopHealthUpdate() {
    if (healthUpdateInterval) {
        clearInterval(healthUpdateInterval);
        healthUpdateInterval = null;
        NotificationManager.info('实时更新', '已停止实时更新系统状态');
    }
}

// 当切换到健康检查面板时自动开始实时更新
function switchFabPanel(btn, target) {
    // 停止之前的所有定时器
    stopHealthUpdate();
    
    // 切换面板
    document.querySelectorAll('.fab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    document.querySelectorAll('.config-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById('panel-' + target).classList.add('active');
    
    // 如果切换到数据库面板，自动加载数据库状态
    if (target === 'dbstatus') {
        checkDatabaseFull();
    }
    
    // 如果切换到健康检查面板，先加载健康状态，然后开始实时更新
    if (target === 'health') {
        // 先加载健康状态数据
        loadHealthStatus();
        // 延迟1秒后开始实时更新，确保DOM元素已创建
        setTimeout(() => {
            startHealthUpdate();
        }, 1000);
    }
}

// 在页面加载时显示欢迎通知
window.addEventListener('load', function() {
    setTimeout(() => {
        NotificationManager.success('欢迎使用', 'FNOS日志监控推送系统已成功加载');
    }, 1000);
});

// 简单测试
console.log('=== 页面加载完成 ===');
console.log('Font Awesome 已加载:', document.querySelector('link[href*="font-awesome"]') !== null);

// 记录最后的历史记录索引，用于检测新增（全局变量）
let lastHistoryIndex = null;

// 主题管理
const ThemeManager = {
    // 主题列表（5个精选主题）
    themes: [
        'default', 'dark', 'ocean', 'green', 'sunset'
    ],

    // 主题名称映射
    themeNames: {
        'default': '暗夜紫',
        'dark':    '深色模式',
        'ocean':   '深海蓝',
        'green':   '清新绿',
        'sunset':  '暮色橙'
    },
    
    // 获取当前主题
    getCurrentTheme() {
        return localStorage.getItem('currentTheme') || 'default';
    },
    
    // 设置主题
    setTheme(themeName) {
        // 移除所有主题类
        this.themes.forEach(theme => {
            document.body.classList.remove(`theme-${theme}`);
        });
        
        // 添加新主题类
        if (themeName !== 'default') {
            document.body.classList.add(`theme-${themeName}`);
        }

        // 保存到本地存储
        localStorage.setItem('currentTheme', themeName);

        // 更新主题单选框的选中状态
        this.updateThemeRadioButtons(themeName);

        console.log(`主题已切换为: ${this.themeNames[themeName]}`);
    },

    // 更新主题单选框的选中状态
    updateThemeRadioButtons(themeName) {
        const radioButton = document.querySelector(`input[name="theme"][value="${themeName}"]`);
        if (radioButton) {
            radioButton.checked = true;
        }
    },

    // 初始化主题
    initTheme() {
        let currentTheme = this.getCurrentTheme();
        
        // 检查系统深色模式设置（如果没有手动设置过主题）
        if (currentTheme === 'default') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) {
                currentTheme = 'dark';
            }
        }
        
        this.setTheme(currentTheme);

        // 绑定主题切换事件（单选框）
        document.querySelectorAll('input[name="theme"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const theme = e.target.value;
                this.setTheme(theme);
            });
        });
        
        // 监听系统主题变化
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            // 只有在使用默认主题时才响应系统变化
            if (this.getCurrentTheme() === 'default') {
                const newTheme = e.matches ? 'dark' : 'default';
                this.setTheme(newTheme);
            }
        });
    }
};

// 在页面上显示调试信息
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== DOMContentLoaded 事件触发 ===');

    let currentConfig = {};

    // 启动session定时检查
    startSessionCheck();

    // 检查会话状态并加载用户信息
    checkSession();

    // 初始化主题
    ThemeManager.initTheme();

    // ========== WebSocket 实时推送初始化 ==========
    // 连接 WebSocket
    wsManager.connect();

    // 监听新日志事件
    wsManager.on('new_logs', (data) => {
        console.log('WebSocket收到新日志:', data);
        // 如果页面正在显示日志，刷新一次
        if (typeof loadLogs === 'function') {
            loadLogs();
        }
        // 更新状态显示
        loadStatus();
    });

    // 监听推送结果事件
    wsManager.on('push_result', (data) => {
        console.log('WebSocket收到推送结果:', data);
        // 可以显示通知或更新UI
        if (Notification.permission === 'granted') {
            new Notification('推送结果', {
                body: `推送${data.success ? '成功' : '失败'}`,
                icon: data.success ? '✓' : '✗'
            });
        }
    });

    // 监听连接状态
    wsManager.on('connected', () => {
        console.log('WebSocket已连接');
        updateConnectionStatus(true);
    });

    wsManager.on('disconnected', () => {
        console.log('WebSocket已断开');
        updateConnectionStatus(false);
    });

    // 更新连接状态显示
    function updateConnectionStatus(connected) {
        let statusEl = document.getElementById('ws-status');
        if (!statusEl) {
            // 如果没有状态元素，可以创建一个小的状态指示器
            statusEl = document.createElement('span');
            statusEl.id = 'ws-status';
            statusEl.className = 'badge bg-secondary ms-2';
            const navBrand = document.querySelector('.navbar-brand');
            if (navBrand) navBrand.appendChild(statusEl);
        }
        statusEl.textContent = connected ? '实时在线' : '实时离线';
        statusEl.className = connected ? 'badge badge-online bg-success ms-2' : 'badge bg-danger ms-2';
    }

    // 页面加载时初始化
    console.log('开始执行初始化...');
    
    // 获取页面加载进度条和骨架屏
    const pageLoader = document.getElementById('pageLoader');
    const skeletonLoader = document.getElementById('skeleton-loader');
    const realContent = document.getElementById('real-content');
    
    // 显示骨架屏，隐藏真实内容
    if (skeletonLoader && realContent) {
        skeletonLoader.style.display = 'block';
        realContent.style.display = 'none';
    }
    
    // 统一初始化：同时获取所有状态
    Promise.all([
        loadStatus(),
        loadConfig(),
        checkDatabase() // 包含日志数据库、备份数据库状态的统一获取
    ]).then(() => {
        loadHistory();
        // 数据加载完成后完成过渡
        finishLoading();
    }).catch(() => {
        // 出错也要完成过渡
        finishLoading();
    });
    
    // 加载完成过渡函数
    function finishLoading() {
        // 隐藏进度条
        if (pageLoader) {
            pageLoader.style.opacity = '0';
            setTimeout(() => pageLoader.remove(), 300);
        }
        
        // 切换骨架屏到真实内容
        if (skeletonLoader && realContent) {
            skeletonLoader.style.display = 'none';
            realContent.style.display = 'block';
        }
    }
    
    // 每15秒更新状态（loadStatus内部已包含备份状态获取）
    setInterval(() => {
        loadStatus();
        checkDatabase(); // 定期刷新数据库面板
    }, 15000);

    // 监听推送历史 Tab 切换，自动加载数据
    const historyTabEl = document.getElementById('history-tab');
    if (historyTabEl) {
        historyTabEl.addEventListener('shown.bs.tab', function () {
            loadHistory();
        });
    }
});

// 计算相对时间
function formatRelativeTime(timestamp) {
    if (!timestamp) return '';
    
    const now = new Date();
    const time = new Date(timestamp);
    const diff = now - time;
    
    if (diff < 0) return '刚刚';
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    
    // 超过7天显示具体日期
    return time.toLocaleDateString('zh-CN');
}

// 加载状态
function loadStatus() {
    // 同时获取状态和备份数据库状态
    return Promise.all([
        apiFetch('/api/status').then(r => r.json()).catch(() => ({ error: '请求失败' })),
        apiFetch('/api/backup/status').then(r => r.json()).catch(() => ({ db_available: false }))
    ])
        .then(([data, backupData]) => {
            if (data.error) {
                document.getElementById('monitor-status').className = 'badge badge-offline';
                document.getElementById('monitor-status').textContent = '异常';
                document.getElementById('monitor-status').setAttribute('aria-label', '监控状态：异常');
                return;
            }

            // 更新状态面板
            const statusBadge = document.getElementById('monitor-status');
            statusBadge.className = data.running ? 'badge badge-online' : 'badge badge-offline';
            statusBadge.textContent = data.running ? '运行中' : '已停止';
            statusBadge.setAttribute('aria-label', '监控状态：' + (data.running ? '运行中' : '已停止'));

            document.getElementById('last-id').textContent = data.last_id;
            document.getElementById('history-count').textContent = data.history_count + ' 条';
            document.getElementById('check-interval').textContent = data.config.check_interval + ' 秒';

            // 更新最后日志ID的相对时间
            const lastIdRelativeEl = document.getElementById('last-id-relative');
            if (lastIdRelativeEl) {
                const lastIdTime = data.last_history_timestamp;
                if (lastIdTime && lastIdTime !== '-') {
                    const time = new Date(lastIdTime);
                    const timeStr = time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    lastIdRelativeEl.textContent = timeStr + ' · ' + formatRelativeTime(lastIdTime);
                } else {
                    lastIdRelativeEl.textContent = '';
                }
            }

            // 更新数据库状态指示器
            const dbStatusIndicator = document.getElementById('db-status-indicator');
            const connectionStatus = data.db_connection_status || '未连接';

            // 根据连接状态设置样式和文字
            if (connectionStatus === '已连接') {
                dbStatusIndicator.className = 'badge badge-online';
            } else if (connectionStatus === '连接失败') {
                dbStatusIndicator.className = 'badge badge-offline';
            } else {
                dbStatusIndicator.className = 'badge bg-secondary';
            }
            dbStatusIndicator.textContent = connectionStatus;
            dbStatusIndicator.setAttribute('aria-label', '日志数据库：' + connectionStatus);

            // 更新备份数据库状态指示器（实时检查）
            const backupDbStatusIndicator = document.getElementById('backup-db-status-indicator');
            const backupDbStatus = backupData.db_available ? '已连接' : '未连接';

            if (backupData.db_available) {
                backupDbStatusIndicator.className = 'badge badge-online';
            } else {
                backupDbStatusIndicator.className = 'badge badge-offline';
            }
            backupDbStatusIndicator.textContent = backupDbStatus;
            backupDbStatusIndicator.setAttribute('aria-label', '备份数据库：' + backupDbStatus);

            // 更新最后备份时间和相对时间
            const lastBackupTimeEl = document.getElementById('last-backup-time');
            const lastBackupRelativeEl = document.getElementById('last-backup-relative');
            if (lastBackupTimeEl && lastBackupRelativeEl) {
                const backupTime = backupData.last_backup_time || backupData.last_finished_time;
                if (backupTime && backupTime !== '-') {
                    const time = new Date(backupTime);
                    const timeStr = time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    lastBackupTimeEl.textContent = timeStr;
                    lastBackupRelativeEl.textContent = '· ' + formatRelativeTime(backupTime);
                } else {
                    lastBackupTimeEl.textContent = '-';
                    lastBackupRelativeEl.textContent = '';
                }
            }

            // 如果连接状态是"连接失败",记录警告并显示通知
            if (connectionStatus === '连接失败') {
                console.warn('数据库连接失败,请检查数据库配置');
                NotificationManager.warning('数据库连接失败', '请检查数据库配置和路径');
            }
            
            // 如果监控状态从停止变为运行，显示通知
            if (data.running) {
                console.log('监控已启动');
            }

            currentConfig = data.config;

            // 渲染系统状态面板里的告警聚合统计行
            const aggStats = data.alert_aggregation;
            const aggRow = document.getElementById('agg-status-row');
            if (aggStats && aggStats.enabled) {
                if (aggRow) aggRow.style.display = '';
                const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
                setEl('status-agg-total',      aggStats.total_received   ?? '-');
                setEl('status-agg-passed',     aggStats.total_pushed     ?? '-');
                setEl('status-agg-suppressed', aggStats.total_suppressed ?? '-');
                setEl('status-agg-silenced',   aggStats.total_silenced   ?? '-');
            } else {
                if (aggRow) aggRow.style.display = 'none';
            }

            // 检查历史记录是否增加，自动刷新历史列表
            checkAndRefreshHistory(data);
        })
        .catch(error => {
            console.error('加载状态失败:', error);
        });
    
    return Promise.resolve();
}

// 加载备份数据库状态（独立定时更新）
function loadBackupDbStatus() {
    apiFetch('/api/backup/status')
        .then(r => r.json())
        .then(data => {
            const backupDbStatusIndicator = document.getElementById('backup-db-status-indicator');
            const backupDbStatus = data.db_available ? '已连接' : '未连接';

            if (data.db_available) {
                backupDbStatusIndicator.className = 'badge badge-online';
            } else {
                backupDbStatusIndicator.className = 'badge badge-offline';
            }
            backupDbStatusIndicator.textContent = backupDbStatus;
            backupDbStatusIndicator.setAttribute('aria-label', '备份数据库：' + backupDbStatus);

            // 更新最后备份时间和相对时间
            const lastBackupTimeEl = document.getElementById('last-backup-time');
            const lastBackupRelativeEl = document.getElementById('last-backup-relative');
            if (lastBackupTimeEl && lastBackupRelativeEl) {
                const backupTime = data.last_backup_time || data.last_finished_time;
                if (backupTime && backupTime !== '-') {
                    const time = new Date(backupTime);
                    const timeStr = time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    lastBackupTimeEl.textContent = timeStr;
                    lastBackupRelativeEl.textContent = '· ' + formatRelativeTime(backupTime);
                } else {
                    lastBackupTimeEl.textContent = '-';
                    lastBackupRelativeEl.textContent = '';
                }
            }
        })
        .catch(error => {
            const backupDbStatusIndicator = document.getElementById('backup-db-status-indicator');
            backupDbStatusIndicator.className = 'badge badge-offline';
            backupDbStatusIndicator.textContent = '未连接';
            backupDbStatusIndicator.setAttribute('aria-label', '备份数据库：未连接');
        });
}

// 检查并刷新历史记录
function checkAndRefreshHistory(data) {
    const currentHistoryIndex = data.last_history_index || data.history_count || 0;

    // 首次加载，只记录索引，不触发通知
    if (lastHistoryIndex === null) {
        console.log('首次加载，记录历史索引:', currentHistoryIndex);
        lastHistoryIndex = currentHistoryIndex;
        return;
    }

    // 如果历史记录数量增加（说明有新推送），自动刷新历史列表
    if (currentHistoryIndex > lastHistoryIndex) {
        console.log('检测到新的推送，自动刷新历史列表');
        console.log('旧的索引:', lastHistoryIndex, '新的索引:', currentHistoryIndex);

        lastHistoryIndex = currentHistoryIndex;

        // 显示提示
        showNewPushNotification();

        // 刷新历史列表
        loadHistory();
    }
}

// 显示新推送通知
function showNewPushNotification() {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = 'alert alert-success mb-0 js-toast';

    const currentTheme = ThemeManager.getCurrentTheme();

    // 主题适配（复用 showNotification 的颜色映射逻辑）
    const themeColors = {
        default: { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.45)',  color: '#d1fae5' },
        dark:    { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.45)',  color: '#d1fae5' },
        ocean:   { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.45)',  color: '#d1fae5' },
        green:   { bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.35)',  color: '#065f46' },
        sunset:  { bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.35)',  color: '#064e3b' },
    };

    const colors = themeColors[currentTheme] || themeColors.default;
    // 使用 background 简写属性而非 background-color，避免被 CSS 的 background 简写覆盖
    const extraStyle = `background:${colors.bg} !important; border-color:${colors.border} !important; color:${colors.color} !important;`;

    const darkThemes = ['dark', 'ocean'];
    const isDark = darkThemes.includes(currentTheme);
    const closeBtnStyle = isDark ? 'filter:invert(1) grayscale(100%) brightness(200%);' : '';

    notification.style.cssText = `position:fixed; top:20px; right:20px; min-width:300px; animation:slideIn 0.3s ease-out; ${extraStyle}`;
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-bell me-2 fa-bounce"></i>
            <span>检测到新的推送，历史已更新</span>
            <button type="button" class="btn-close ms-auto" style="${closeBtnStyle}" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    // 添加动画样式
    if (!document.getElementById('notification-animation')) {
        const style = document.createElement('style');
        style.id = 'notification-animation';
        style.textContent = `
            @keyframes slideIn {
                from { opacity: 0; transform: translateX(100px); }
                to { opacity: 1; transform: translateX(0); }
            }
        `;
        document.head.appendChild(style);
    }

    // 添加到页面
    document.body.appendChild(notification);

    // 3秒后自动消失
    setTimeout(() => {
        notification.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 加载配置
function loadConfig() {
    apiFetch('/api/config')
        .then(response => response.json())
        .then(config => {
            currentConfig = config;

            // 填充表单
            document.getElementById('database-path').value = config.database_path;
            document.getElementById('check-interval-input').value = config.check_interval;
            document.getElementById('webhook-url').value = config.webhook_url || '';
            // 保持 password 类型，用眼睛按钮切换可见性（URL 中常含 token 参数）

            // 填充推送渠道设置
            const pushChannels = config.push_channels || {'webhook': true, 'wecom': false};
            document.getElementById('push-webhook-enabled').checked = pushChannels.webhook || false;
            document.getElementById('push-wecom-enabled').checked = pushChannels.wecom || false;
            document.getElementById('push-dingtalk-enabled').checked = pushChannels.dingtalk || false;
            document.getElementById('push-feishu-enabled').checked = pushChannels.feishu || false;
            document.getElementById('push-bark-enabled').checked = pushChannels.bark || false;
            document.getElementById('push-pushplus-enabled').checked = pushChannels.pushplus || false;
            document.getElementById('push-meow-enabled').checked = pushChannels.meow || false;

            // 填充企业微信配置
            const wecomConfig = config.wecom || {};
            document.getElementById('wecom-webhook-url').value = wecomConfig.webhook_url || '';
            // 保持 password 类型，用眼睛按钮切换可见性

            // 填充钉钉配置
            const dingtalkConfig = config.dingtalk || {};
            document.getElementById('dingtalk-webhook-url').value = dingtalkConfig.webhook_url || '';
            document.getElementById('dingtalk-secret').value = dingtalkConfig.secret || '';

            // 填充飞书配置
            const feishuConfig = config.feishu || {};
            document.getElementById('feishu-webhook-url').value = feishuConfig.webhook_url || '';

            // 填充Bark配置
            const barkConfig = config.bark || {};
            document.getElementById('bark-device-key').value = barkConfig.device_key || '';
            document.getElementById('bark-server').value = barkConfig.server || 'https://api.day.app';

            // 填充PushPlus配置
            const pushplusConfig = config.pushplus || {};
            document.getElementById('pushplus-token').value = pushplusConfig.token || '';
            document.getElementById('pushplus-topic').value = pushplusConfig.topic || '';

            // 填充MeoW设置
            const meowConfig = config.meow || {};
            document.getElementById('push-meow-enabled').checked = meowConfig.enabled || false;
            document.getElementById('meow-nickname').value = meowConfig.nickname || '';
            document.getElementById('meow-title').value = meowConfig.title || '';
            document.getElementById('meow-msgtype').value = meowConfig.msgtype || '';

            // 填充免打扰设置
            const dndConfig = config.do_not_disturb || {};
            document.getElementById('dnd-enabled').checked = dndConfig.enabled || false;
            document.getElementById('dnd-start-time').value = dndConfig.start_time || '23:00';
            document.getElementById('dnd-end-time').value = dndConfig.end_time || '08:00';

            // 填充主题设置
            const currentTheme = config.theme || 'default';
            const themeRadio = document.querySelector(`input[name="theme"][value="${currentTheme}"]`);
            if (themeRadio) {
                themeRadio.checked = true;
            }

            // 填充告警聚合与降噪配置
            const aggConfig = config.alert_aggregation || {};
            document.getElementById('alert-agg-enabled').checked = aggConfig.enabled !== false;
            document.getElementById('alert-agg-window').value = aggConfig.window_seconds || 300;
            document.getElementById('alert-agg-threshold').value = aggConfig.threshold || 5;
            document.getElementById('alert-agg-silence').value = aggConfig.silence_seconds || 600;
            // 若已启用，立即加载并展示统计条
            if (aggConfig.enabled !== false) {
                loadAggStats();
            }

            // 填充备份监控设置
            const backupConfig = config.backup_monitor || {};
            document.getElementById('backup-monitor-enabled').checked = backupConfig.enabled || false;
            document.getElementById('backup-db-path').value = backupConfig.database_path || '';
            document.getElementById('backup-check-interval').value = backupConfig.check_interval || 10;
            
            // 填充状态筛选
            const statusFilter = backupConfig.status_filter || [1, 2, 3, 4];
            for (let i = 1; i <= 4; i++) {
                const checkbox = document.getElementById('backup-status-' + i);
                if (checkbox) {
                    checkbox.checked = statusFilter.includes(i);
                }
            }

            // 生成日志级别复选框，带图标
            const levelsContainer = document.getElementById('log-levels');
            levelsContainer.innerHTML = '';

            // 日志级别对应的图标和颜色
            const levelIcons = {
                '调试': { icon: 'fa-bug', color: '#6c757d' },
                '普通': { icon: 'fa-info-circle', color: '#4facfe' },
                '警告': { icon: 'fa-exclamation-triangle', color: '#fa709a' },
                '错误': { icon: 'fa-times-circle', color: '#ff6b6b' },
                '严重错误': { icon: 'fa-fire', color: '#dc3545' }
            };

            config.log_levels.forEach(level => {
                const isChecked = config.selected_levels.includes(level);
                const iconInfo = levelIcons[level] || { icon: 'fa-circle', color: '#667eea' };

                const checkboxHTML = `
                    <div class="form-check form-check-inline">
                        <input class="form-check-input" type="checkbox"
                               id="level-${level}" value="${level}" ${isChecked ? 'checked' : ''}>
                        <label class="form-check-label" for="level-${level}" style="cursor: pointer;">
                            <i class="fas ${iconInfo.icon} me-1" style="color: ${iconInfo.color};"></i>
                            <span style="color: ${iconInfo.color}; font-weight: 500;">${level}</span>
                        </label>
                    </div>
                `;
                levelsContainer.innerHTML += checkboxHTML;
            });

            // 生成事件类型复选框
            const eventsContainer = document.getElementById('event-types');
            eventsContainer.innerHTML = '';

            // 所有可能的事件类型，按类别分组
            const eventCategories = {
                '登录认证': [
                    { id: 'LoginSucc', icon: 'fa-sign-in-alt', color: '#4facfe', name: '登录成功' },
                    { id: 'LoginSucc2FA1', icon: 'fa-shield-alt', color: '#667eea', name: '登录成功(双因素)' },
                    { id: 'LoginFail', icon: 'fa-times-circle', color: '#ff6b6b', name: '登录失败' },
                    { id: 'Logout', icon: 'fa-sign-out-alt', color: '#fa709a', name: '退出' }
                ],
                'SSH连接': [
                    { id: 'SSH_INVALID_USER', icon: 'fa-user-shield', color: '#ff9f43', name: 'SSH无效用户' },
                    { id: 'SSH_AUTH_FAILED', icon: 'fa-lock', color: '#ee5a6f', name: 'SSH认证失败' },
                    { id: 'SSH_DISCONNECTED', icon: 'fa-plug', color: '#6c757d', name: 'SSH断开连接' },
                    { id: 'SshdLoginSucc', icon: 'fa-check-circle', color: '#00b09b', name: 'SSH登录成功' }
                ],
                '文件操作': [
                    { id: 'CreateFile', icon: 'fa-file-medical', color: '#00b09b', name: '创建文件' },
                    { id: 'DeleteFile', icon: 'fa-file-medical-alt', color: '#dc3545', name: '删除文件' },
                    { id: 'CopyFile', icon: 'fa-file-copy', color: '#4facfe', name: '复制文件' },
                    { id: 'MoveFile', icon: 'fa-file-export', color: '#667eea', name: '移动文件' },
                    { id: 'RenameFile', icon: 'fa-file-signature', color: '#e83e8c', name: '重命名文件' },
                    { id: 'RestoreFile', icon: 'fa-undo-alt', color: '#00b09b', name: '文件还原' },
                    { id: 'ModifyFile', icon: 'fa-file-code', color: '#ffc107', name: '修改文件' },
                    { id: 'FileUpload', icon: 'fa-file-upload', color: '#00b09b', name: '文件上传' },
                    { id: 'FileDownload', icon: 'fa-file-download', color: '#667eea', name: '文件下载' },
                    { id: 'FileAccess', icon: 'fa-folder-open', color: '#4facfe', name: '访问文件' },
                    { id: 'FilePermission', icon: 'fa-unlock', color: '#fd7e14', name: '文件权限变更' },
                    { id: 'FileSync', icon: 'fa-sync-alt', color: '#00b09b', name: '文件同步' },
                    { id: 'FileCompress', icon: 'fa-file-archive', color: '#e83e8c', name: '文件压缩' },
                    { id: 'FileExtract', icon: 'fa-file-zipper', color: '#e83e8c', name: '文件解压' },
                    { id: 'FileEncrypt', icon: 'fa-file-shield', color: '#667eea', name: '文件加密' },
                    { id: 'FileDecrypt', icon: 'fa-file-unlock', color: '#667eea', name: '文件解密' },
                    { id: 'FileBackup', icon: 'fa-save', color: '#00b09b', name: '文件备份' },
                    { id: 'FileRestore', icon: 'fa-undo', color: '#4facfe', name: '文件恢复' }
                ],
                '应用管理': [
                    { id: 'APP_CRASH', icon: 'fa-bomb', color: '#dc3545', name: '应用崩溃' },
                    { id: 'APP_UPDATE_FAILED', icon: 'fa-exclamation-triangle', color: '#ff6b6b', name: '应用更新失败' },
                    { id: 'APP_START_FAILED', icon: 'fa-power-off', color: '#fa709a', name: '应用启动失败' },
                    { id: 'APP_INSTALL_FAILED', icon: 'fa-exclamation-circle', color: '#dc3545', name: '应用安装失败' },
                    { id: 'APP_INSTALL_FAILED_EXEC_INIT_EXCEPTION', icon: 'fa-exclamation-triangle', color: '#ff6b6b', name: '安装失败(初始化异常)' },
                    { id: 'APP_INSTALL_FAILED_INSTALL_CALLBACK_EXCEPTION', icon: 'fa-exclamation-triangle', color: '#ff6b6b', name: '安装失败(回调异常)' },
                    { id: 'APP_INSTALL_FAILED_INSTALL_MODEL_NOT_MATCH', icon: 'fa-exclamation-triangle', color: '#ff6b6b', name: '安装失败(模型不匹配)' },
                    { id: 'APP_START_FAILED_LOCAL_APP_RUN_EXCEPTION', icon: 'fa-bug', color: '#fd7e14', name: '启动失败(应用异常)' },
                    { id: 'LOCAL_APP_RUN_EXCEPTION', icon: 'fa-bug', color: '#fd7e14', name: '本地应用异常' },
                    { id: 'APP_AUTO_START_FAILED_DOCKER_NOT_AVAILABLE', icon: 'fa-docker', color: '#e83e8c', name: '自动启动失败(Docker)' },
                    { id: 'APP_STARTED', icon: 'fa-play', color: '#4facfe', name: '应用已启动' },
                    { id: 'APP_STOPPED', icon: 'fa-stop', color: '#fa709a', name: '应用已停止' },
                    { id: 'APP_UPDATED', icon: 'fa-sync', color: '#00b09b', name: '应用已更新' },
                    { id: 'APP_INSTALLED', icon: 'fa-download', color: '#4facfe', name: '应用已安装' },
                    { id: 'APP_AUTO_STARTED', icon: 'fa-rocket', color: '#667eea', name: '应用自动启动' },
                    { id: 'APP_UNINSTALLED', icon: 'fa-trash', color: '#dc3545', name: '应用已卸载' },
                    { id: 'APP_INSTALL_FAILED_DEPENDENCT_AND_CONFLICT', icon: 'fa-exclamation-triangle', color: '#dc3545', name: '应用安装失败(依赖冲突)' }
                ],
                '系统监控': [
                    { id: 'CPU_USAGE_ALARM', icon: 'fa-microchip', color: '#ffc107', name: 'CPU使用率告警' },
                    { id: 'CPU_USAGE_RESTORED', icon: 'fa-check-double', color: '#4facfe', name: 'CPU使用率恢复' },
                    { id: 'CPU_TEMPERATURE_ALARM', icon: 'fa-thermometer-full', color: '#ff6b6b', name: 'CPU温度告警' },
                    { id: 'MemoryUsageAlarm', icon: 'fa-memory', color: '#e83e8c', name: '内存使用告警' },
                    { id: 'MEMORY_USAGE_ALARM', icon: 'fa-microchip', color: '#ff6b6b', name: '内存使用率告警' },
                    { id: 'MEMORY_USAGE_RESTORED', icon: 'fa-check-double', color: '#667eea', name: '内存使用率恢复' },
                    { id: 'DiskUsageAlarm', icon: 'fa-chart-pie', color: '#ff9f43', name: '磁盘使用告警' },
                    { id: 'NetworkUsageAlarm', icon: 'fa-network-wired', color: '#667eea', name: '网络流量告警' },
                    { id: 'ProcessHighCPU', icon: 'fa-tasks', color: '#fd7e14', name: '进程高CPU占用' },
                    { id: 'ProcessHighMemory', icon: 'fa-tasks', color: '#e83e8c', name: '进程高内存占用' }
                ],
                'UPS电源': [
                    { id: 'UPS_ONBATT', icon: 'fa-battery-quarter', color: '#fd7e14', name: 'UPS电池供电' },
                    { id: 'UPS_ONBATT_LOWBATT', icon: 'fa-battery-empty', color: '#dc3545', name: 'UPS低电量' },
                    { id: 'UPS_ONLINE', icon: 'fa-battery-full', color: '#00b09b', name: 'UPS在线' },
                    { id: 'UPS_ENABLE', icon: 'fa-power-off', color: '#4facfe', name: 'UPS启用' },
                    { id: 'UPS_DISABLE', icon: 'fa-toggle-off', color: '#6c757d', name: 'UPS禁用' }
                ],
                '磁盘管理': [
                    { id: 'FoundDisk', icon: 'fa-hdd', color: '#00b09b', name: '发现磁盘' },
                    { id: 'DiskWakeup', icon: 'fa-play-circle', color: '#00b09b', name: '磁盘唤醒' },
                    { id: 'DiskSpindown', icon: 'fa-pause-circle', color: '#6c757d', name: '磁盘休眠' },
                    { id: 'DISK_IO_ERR', icon: 'fa-exclamation-circle', color: '#ff6b6b', name: '磁盘IO错误' },
                    { id: 'DiskFull', icon: 'fa-hdd', color: '#dc3545', name: '磁盘空间不足' },
                    { id: 'DiskCorrupt', icon: 'fa-hdd', color: '#dc3545', name: '磁盘损坏' },
                    { id: 'DiskFormat', icon: 'fa-hdd', color: '#e83e8c', name: '磁盘格式化' },
                    { id: 'DiskPartition', icon: 'fa-hdd', color: '#667eea', name: '磁盘分区' }
                ],
                '存储管理': [
                    { id: 'CreateStorage', icon: 'fa-hdd', color: '#00b09b', name: '创建存储' },
                    { id: 'MountStorage', icon: 'fa-plug', color: '#4facfe', name: '挂载存储' },
                    { id: 'UnmountStorage', icon: 'fa-eject', color: '#ffc107', name: '卸载存储' },
                    { id: 'DeleteStorage', icon: 'fa-trash', color: '#dc3545', name: '删除存储' },
                    { id: 'STORAGE_MOUNT_SUCCESS', icon: 'fa-check-circle', color: '#00b09b', name: '存储挂载成功' },
                    { id: 'STORAGE_MOUNT_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: '存储挂载失败' },
                    { id: 'STORAGE_UMOUNT_SUCCESS', icon: 'fa-check-circle', color: '#00b09b', name: '存储卸载成功' },
                    { id: 'STORAGE_UMOUNT_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: '存储卸载失败' }
                ],
                '防火墙': [
                    { id: 'FW_ENABLE', icon: 'fa-shield-alt', color: '#00b09b', name: '防火墙启用' },
                    { id: 'FW_DISABLE', icon: 'fa-shield-alt', color: '#6c757d', name: '防火墙禁用' },
                    { id: 'FW_START_SUCCESS', icon: 'fa-check-circle', color: '#00b09b', name: '防火墙启动成功' },
                    { id: 'FW_START_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: '防火墙启动失败' },
                    { id: 'FW_STOP_SUCCESS', icon: 'fa-check-circle', color: '#00b09b', name: '防火墙停止成功' },
                    { id: 'FW_STOP_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: '防火墙停止失败' }
                ],
                '共享协议': [
                    // NFS事件
                    { id: 'NFS_MOUNT_SUCCESS', icon: 'fa-folder-open', color: '#00b09b', name: 'NFS挂载成功', protocol: 'NFS' },
                    { id: 'NFS_MOUNT_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'NFS挂载失败', protocol: 'NFS' },
                    { id: 'NFS_UMOUNT', icon: 'fa-folder', color: '#6c757d', name: 'NFS卸载', protocol: 'NFS' },
                    { id: 'NFS_ACCESS_DENIED', icon: 'fa-ban', color: '#ff6b6b', name: 'NFS访问拒绝', protocol: 'NFS' },
                    { id: 'NFS_TIMEOUT', icon: 'fa-clock', color: '#fd7e14', name: 'NFS超时', protocol: 'NFS' },
                    { id: 'NFS_ENABLED', icon: 'fa-toggle-on', color: '#00b09b', name: 'NFS启用', protocol: 'NFS' },
                    { id: 'NFS_DISABLED', icon: 'fa-toggle-off', color: '#6c757d', name: 'NFS禁用', protocol: 'NFS' },
                    // SMB/CIFS事件
                    { id: 'SAMBA_CONNECT_SUCCESS', icon: 'fa-share-alt', color: '#00b09b', name: 'SMB连接成功', protocol: 'SMB' },
                    { id: 'SAMBA_CONNECT_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'SMB连接失败', protocol: 'SMB' },
                    { id: 'SAMBA_DISCONNECT', icon: 'fa-unlink', color: '#6c757d', name: 'SMB断开连接', protocol: 'SMB' },
                    { id: 'SAMBA_AUTH_FAILED', icon: 'fa-lock', color: '#ff6b6b', name: 'SMB认证失败', protocol: 'SMB' },
                    { id: 'SAMBA_SHARE_CREATED', icon: 'fa-plus-circle', color: '#4facfe', name: 'SMB共享创建', protocol: 'SMB' },
                    { id: 'SAMBA_SHARE_DELETED', icon: 'fa-minus-circle', color: '#dc3545', name: 'SMB共享删除', protocol: 'SMB' },
                    { id: 'SAMBA_SHARE_MODIFIED', icon: 'fa-edit', color: '#ffc107', name: 'SMB共享修改', protocol: 'SMB' },
                    { id: 'SAMBA_ACCESS_DENIED', icon: 'fa-ban', color: '#ff6b6b', name: 'SMB访问拒绝', protocol: 'SMB' },
                    { id: 'SAMBA_ENABLED', icon: 'fa-toggle-on', color: '#00b09b', name: 'SMB启用', protocol: 'SMB' },
                    { id: 'SAMBA_DISABLED', icon: 'fa-toggle-off', color: '#6c757d', name: 'SMB禁用', protocol: 'SMB' },
                    { id: 'SAMBA_SESSION_OPEN', icon: 'fa-sign-in-alt', color: '#4facfe', name: 'SAMBA会话打开', protocol: 'SMB' },
                    { id: 'SAMBA_SESSION_CLOSE', icon: 'fa-sign-out-alt', color: '#6c757d', name: 'SAMBA会话关闭', protocol: 'SMB' },
                    // FTP事件
                    { id: 'FTP_LOGIN_SUCCESS', icon: 'fa-sign-in-alt', color: '#00b09b', name: 'FTP登录成功', protocol: 'FTP' },
                    { id: 'FTP_LOGIN_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'FTP登录失败', protocol: 'FTP' },
                    { id: 'FTP_DISCONNECT', icon: 'fa-sign-out-alt', color: '#6c757d', name: 'FTP断开连接', protocol: 'FTP' },
                    { id: 'FTP_UPLOAD_START', icon: 'fa-upload', color: '#667eea', name: 'FTP上传开始', protocol: 'FTP' },
                    { id: 'FTP_UPLOAD_SUCCESS', icon: 'fa-check-circle', color: '#00b09b', name: 'FTP上传成功', protocol: 'FTP' },
                    { id: 'FTP_UPLOAD_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'FTP上传失败', protocol: 'FTP' },
                    { id: 'FTP_DOWNLOAD_START', icon: 'fa-download', color: '#667eea', name: 'FTP下载开始', protocol: 'FTP' },
                    { id: 'FTP_DOWNLOAD_SUCCESS', icon: 'fa-check-circle', color: '#00b09b', name: 'FTP下载成功', protocol: 'FTP' },
                    { id: 'FTP_DOWNLOAD_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'FTP下载失败', protocol: 'FTP' },
                    { id: 'FTP_DELETE_FILE', icon: 'fa-trash', color: '#dc3545', name: 'FTP删除文件', protocol: 'FTP' },
                    { id: 'FTP_CREATE_DIR', icon: 'fa-folder-plus', color: '#4facfe', name: 'FTP创建目录', protocol: 'FTP' },
                    { id: 'FTP_DELETE_DIR', icon: 'fa-folder-minus', color: '#dc3545', name: 'FTP删除目录', protocol: 'FTP' },
                    { id: 'FTP_ENABLED', icon: 'fa-toggle-on', color: '#00b09b', name: 'FTP启用', protocol: 'FTP' },
                    { id: 'FTP_DISABLED', icon: 'fa-toggle-off', color: '#6c757d', name: 'FTP禁用', protocol: 'FTP' },
                    // AFP事件
                    { id: 'AFP_CONNECT_SUCCESS', icon: 'fa-plug', color: '#00b09b', name: 'AFP连接成功', protocol: 'AFP' },
                    { id: 'AFP_CONNECT_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'AFP连接失败', protocol: 'AFP' },
                    { id: 'AFP_LOGIN_SUCCESS', icon: 'fa-sign-in-alt', color: '#00b09b', name: 'AFP登录成功', protocol: 'AFP' },
                    { id: 'AFP_LOGIN_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'AFP登录失败', protocol: 'AFP' },
                    { id: 'AFP_DISCONNECT', icon: 'fa-unlink', color: '#6c757d', name: 'AFP断开连接', protocol: 'AFP' },
                    { id: 'AFP_VOLUME_MOUNT', icon: 'fa-folder-open', color: '#4facfe', name: 'AFP卷挂载', protocol: 'AFP' },
                    { id: 'AFP_VOLUME_UMOUNT', icon: 'fa-folder', color: '#6c757d', name: 'AFP卷卸载', protocol: 'AFP' },
                    { id: 'AFP_ENABLED', icon: 'fa-toggle-on', color: '#00b09b', name: 'AFP启用', protocol: 'AFP' },
                    { id: 'AFP_DISABLED', icon: 'fa-toggle-off', color: '#6c757d', name: 'AFP禁用', protocol: 'AFP' },
                    // WebDAV事件
                    { id: 'WEBDAV_CONNECT_SUCCESS', icon: 'fa-plug', color: '#00b09b', name: 'WebDAV连接成功', protocol: 'WebDAV' },
                    { id: 'WEBDAV_CONNECT_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'WebDAV连接失败', protocol: 'WebDAV' },
                    { id: 'WEBDAV_AUTH_FAILED', icon: 'fa-lock', color: '#ff6b6b', name: 'WebDAV认证失败', protocol: 'WebDAV' },
                    { id: 'WEBDAV_GET_SUCCESS', icon: 'fa-download', color: '#00b09b', name: 'WebDAV获取成功', protocol: 'WebDAV' },
                    { id: 'WEBDAV_GET_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'WebDAV获取失败', protocol: 'WebDAV' },
                    { id: 'WEBDAV_PUT_SUCCESS', icon: 'fa-upload', color: '#00b09b', name: 'WebDAV上传成功', protocol: 'WebDAV' },
                    { id: 'WEBDAV_PUT_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'WebDAV上传失败', protocol: 'WebDAV' },
                    { id: 'WEBDAV_DELETE_SUCCESS', icon: 'fa-trash', color: '#00b09b', name: 'WebDAV删除成功', protocol: 'WebDAV' },
                    { id: 'WEBDAV_DELETE_FAILED', icon: 'fa-times-circle', color: '#dc3545', name: 'WebDAV删除失败', protocol: 'WebDAV' },
                    { id: 'WEBDAV_ENABLED', icon: 'fa-toggle-on', color: '#00b09b', name: 'WebDAV启用', protocol: 'WebDAV' },
                    { id: 'WEBDAV_DISABLED', icon: 'fa-toggle-off', color: '#6c757d', name: 'WebDAV禁用', protocol: 'WebDAV' },
                    // DLNA事件
                    { id: 'DLNA_ENABLED', icon: 'fa-play-circle', color: '#00b09b', name: 'DLNA启用', protocol: 'DLNA' },
                    { id: 'DLNA_DISABLED', icon: 'fa-pause-circle', color: '#6c757d', name: 'DLNA禁用', protocol: 'DLNA' },
                    // 共享协议事件
                    { id: 'SHARE_EVENTID_PUT', icon: 'fa-upload', color: '#4facfe', name: '共享文件上传', protocol: 'SHARE' },
                    { id: 'SHARE_EVENTID_DEL', icon: 'fa-trash', color: '#dc3545', name: '共享文件删除', protocol: 'SHARE' },
                    { id: 'SHARE_EVENTID_MKDIR', icon: 'fa-folder-plus', color: '#00b09b', name: '共享目录创建', protocol: 'SHARE' },
                    { id: 'SHARE_EVENTID_RENAME', icon: 'fa-file-signature', color: '#ffc107', name: '共享文件重命名', protocol: 'SHARE' }
                ]
            };

            // 按类别生成事件
            Object.keys(eventCategories).forEach(category => {
                const categoryEvents = eventCategories[category];
                const categoryColor = {
                    '登录认证': '#667eea',
                    'SSH连接': '#e83e8c',
                    '文件操作': '#00b09b',
                    '应用管理': '#4facfe',
                    '系统监控': '#ffc107',
                    'UPS电源': '#fd7e14',
                    '磁盘管理': '#17a2b8',
                    '存储管理': '#059669',
                    '防火墙': '#7c3aed',
                    '共享协议': '#e83e8c'
                }[category];

                // 特殊处理：共享协议按协议类型分组
                if (category === '共享协议') {
                    // 按protocol字段分组
                    const protocolGroups = {};
                    categoryEvents.forEach(event => {
                        const protocol = event.protocol || '其他';
                        if (!protocolGroups[protocol]) {
                            protocolGroups[protocol] = [];
                        }
                        protocolGroups[protocol].push(event);
                    });

                    // 协议颜色映射
                    const protocolColors = {
                        'NFS': '#00b09b',
                        'SMB': '#4facfe',
                        'FTP': '#667eea',
                        'AFP': '#e83e8c',
                        'WebDAV': '#ffc107',
                        'DLNA': '#fd7e14',
                        'SHARE': '#17a2b8',
                        '其他': '#6c757d'
                    };

                    // 协议图标映射
                    const protocolIcons = {
                        'NFS': 'fa-network-wired',
                        'SMB': 'fa-share-alt',
                        'FTP': 'fa-upload',
                        'AFP': 'fa-apple',
                        'WebDAV': 'fa-globe',
                        'DLNA': 'fa-tv',
                        'SHARE': 'fa-share',
                        '其他': 'fa-folder'
                    };

                    // 为每个协议创建子分类
                    Object.keys(protocolGroups).forEach(protocol => {
                        const protocolEvents = protocolGroups[protocol];
                        const protocolColor = protocolColors[protocol] || '#6c757d';
                        const protocolIcon = protocolIcons[protocol] || 'fa-folder';

                        const protocolHTML = `
                            <div class="event-category mb-3">
                                <div class="category-header" style="background: linear-gradient(135deg, ${protocolColor}, ${protocolColor}dd); color: white; padding: 10px 15px; border-radius: 10px 10px 0 0; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                                    <i class="fas ${protocolIcon}"></i>
                                    <span>${category} - ${protocol}</span>
                                    <span style="margin-left: 8px; opacity: 0.9; font-size: 0.85em;">${protocolEvents.length} 个事件</span>
                                    <div style="margin-left: auto; display: flex; gap: 8px;">
                                        <button type="button" class="btn btn-sm" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 4px 12px; font-size: 0.8em;" onclick="selectAllInCategory('${category}-${protocol}')">
                                            <i class="fas fa-check-double me-1"></i>全选
                                        </button>
                                        <button type="button" class="btn btn-sm" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 4px 12px; font-size: 0.8em;" onclick="deselectAllInCategory('${category}-${protocol}')">
                                            <i class="fas fa-times me-1"></i>全不选
                                        </button>
                                    </div>
                                </div>
                                <div class="category-events d-flex flex-wrap gap-2 event-category-body" style="padding: 12px; border-radius: 0 0 10px 10px; border: 2px solid ${protocolColor}20; border-top: none;">
                                    ${protocolEvents.map(event => {
                                        const isSelected = config.selected_events && config.selected_events.includes(event.id);
                                        const isChecked = !isSelected;
                                        return `
                                            <div class="event-checkbox event-checkbox-item" style="padding: 6px 12px; border-radius: 12px; border: 2px solid ${event.color}30; transition: all 0.2s ease; cursor: pointer;">
                                                <input class="form-check-input category-${category}-${protocol}" type="checkbox"
                                                       id="event-${event.id}" value="${event.id}" ${isChecked ? 'checked' : ''}
                                                       style="margin: 0 6px 0 0;">
                                                <label for="event-${event.id}" class="event-checkbox-label" style="cursor: pointer; display: flex; align-items: center; gap: 6px; margin: 0; font-size: 0.85em;">
                                                    <i class="fas ${event.icon}" style="color: ${event.color}; font-size: 1em;"></i>
                                                    <span class="event-checkbox-text" style="font-weight: 500;">${event.name}</span>
                                                </label>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            </div>
                        `;
                        eventsContainer.innerHTML += protocolHTML;
                    });
                } else {
                    // 其他分类的普通渲染逻辑
                    const categoryHTML = `
                        <div class="event-category mb-3">
                            <div class="category-header" style="background: linear-gradient(135deg, ${categoryColor}, ${categoryColor}dd); color: white; padding: 10px 15px; border-radius: 10px 10px 0 0; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                                <i class="fas fa-folder-open"></i>
                                <span>${category}</span>
                                <span style="margin-left: 8px; opacity: 0.9; font-size: 0.85em;">${categoryEvents.length} 个事件</span>
                                <div style="margin-left: auto; display: flex; gap: 8px;">
                                    <button type="button" class="btn btn-sm" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 4px 12px; font-size: 0.8em;" onclick="selectAllInCategory('${category}')">
                                        <i class="fas fa-check-double me-1"></i>全选
                                    </button>
                                    <button type="button" class="btn btn-sm" style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 4px 12px; font-size: 0.8em;" onclick="deselectAllInCategory('${category}')">
                                        <i class="fas fa-times me-1"></i>全不选
                                    </button>
                                </div>
                            </div>
                            <div class="category-events d-flex flex-wrap gap-2 event-category-body" style="padding: 12px; border-radius: 0 0 10px 10px; border: 2px solid ${categoryColor}20; border-top: none;">
                                ${categoryEvents.map(event => {
                                    const isSelected = config.selected_events && config.selected_events.includes(event.id);
                                    const isChecked = !isSelected;
                                    return `
                                        <div class="event-checkbox event-checkbox-item" style="padding: 6px 12px; border-radius: 12px; border: 2px solid ${event.color}30; transition: all 0.2s ease; cursor: pointer;">
                                            <input class="form-check-input category-${category}" type="checkbox"
                                                   id="event-${event.id}" value="${event.id}" ${isChecked ? 'checked' : ''}
                                                   style="margin: 0 6px 0 0;">
                                            <label for="event-${event.id}" class="event-checkbox-label" style="cursor: pointer; display: flex; align-items: center; gap: 6px; margin: 0; font-size: 0.85em;">
                                                <i class="fas ${event.icon}" style="color: ${event.color}; font-size: 1em;"></i>
                                                <span class="event-checkbox-text" style="font-weight: 500;">${event.name}</span>
                                            </label>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    `;
                    eventsContainer.innerHTML += categoryHTML;
                }
            });
        });
}

// 关键词搜索：更新 historyKeyword 并重新渲染历史列表（防抖 300ms）
let _historySearchTimer = null;
function onHistorySearch(kw) {
    historyKeyword = kw.trim();
    clearTimeout(_historySearchTimer);
    _historySearchTimer = setTimeout(() => loadHistory(), 300);
}

// 加载推送历史
// historyKeyword 用于关键词高亮（由搜索框驱动）
let historyKeyword = '';
// 分页状态
let historyCurrentPage = 1;  // 当前页码（从1开始）
const historyPageSize = 20;  // 每页显示数量
let historyTotal = 0;  // 总记录数

/**
 * 把文本中的 keyword 用 .kw-highlight span 包裹，用于推送历史预览高亮。
 * @param {string} text  原始文本（已 escapeHtml 过）
 * @param {string} kw    搜索关键词（未 escapeHtml，由用户输入）
 * @returns {string}     含高亮 span 的 HTML
 */
function highlightKeyword(text, kw) {
    if (!kw || kw.trim() === '') return text;
    const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`(${escaped})`, 'gi');
    return text.replace(re, '<mark class="kw-highlight">$1</mark>');
}

function loadHistory(retry = 0) {
    const tbody = document.getElementById('history-table');
    tbody.innerHTML = '<tr><td colspan="7" class="text-center"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">加载中...</span></div> 加载中...</td></tr>';

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    const offset = (historyCurrentPage - 1) * historyPageSize;

    // 构建查询参数，包含日期筛选
    let queryParams = `limit=${historyPageSize}&offset=${offset}`;
    if (historyDateFilter.startDate) {
        queryParams += `&start_date=${historyDateFilter.startDate}`;
    }
    if (historyDateFilter.endDate) {
        queryParams += `&end_date=${historyDateFilter.endDate}`;
    }

    apiFetch(`/api/history?${queryParams}`, { signal: controller.signal })
        .then(response => response.json())
        .then(data => {
            clearTimeout(timeout);
            if (data.error && data.error.includes('监控程序未启动')) {
                if (retry < 1) {
                    setTimeout(() => loadHistory(1), 1500);
                } else {
                    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state">
                        <div class="empty-state__icon"><i class="fas fa-power-off" aria-hidden="true"></i></div>
                        <div class="empty-state__title">监控程序未启动</div>
                        <div class="empty-state__desc">请先启动监控，历史记录将在此显示。</div>
                        <div class="empty-state__action">
                            <button class="btn btn-sm btn-outline-primary me-2" onclick="controlMonitor('start')"><i class="fas fa-play me-1"></i>启动监控</button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="loadHistory()"><i class="fas fa-redo me-1"></i>重试</button>
                        </div>
                    </div></td></tr>`;
                    updatePaginationControls(0);
                }
                return;
            }
            if (!data.data || !Array.isArray(data.data)) {
                if (retry < 1) {
                    setTimeout(() => loadHistory(1), 1500);
                } else {
                    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state">
                        <div class="empty-state__icon"><i class="fas fa-exclamation-circle" aria-hidden="true"></i></div>
                        <div class="empty-state__title">数据加载失败</div>
                        <div class="empty-state__desc">请检查网络或刷新页面重试。</div>
                        <div class="empty-state__action"><button class="btn btn-sm btn-outline-primary" onclick="loadHistory()"><i class="fas fa-redo me-1"></i>重新加载</button></div>
                    </div></td></tr>`;
                    updatePaginationControls(0);
                }
                return;
            }

            const history = data.data;
            historyTotal = data.total || 0;
            updatePaginationControls(historyTotal);

            if (history.length === 0) {
                const hasKeyword = historyKeyword && historyKeyword.trim() !== '';
                const hasDateFilter = historyDateFilter.startDate || historyDateFilter.endDate;

                let emptyMsg = '尚未产生任何推送记录';
                let emptyHint = '启动监控并触发事件后，推送历史将在此显示。';
                let emptyAction = `<button class="btn btn-sm btn-outline-primary" onclick="controlMonitor('start')"><i class="fas fa-play me-1"></i>启动监控</button>`;

                if (hasKeyword && hasDateFilter) {
                    emptyMsg = `未找到包含 "<strong>${escapeHtml(historyKeyword)}</strong>" 且在指定日期范围内的记录`;
                    emptyHint = '请尝试更换关键词或调整日期范围。';
                    emptyAction = `<button class="btn btn-sm btn-outline-secondary me-2" onclick="onHistorySearch('');document.getElementById('history-search').value='';">清除搜索</button>
                                   <button class="btn btn-sm btn-outline-secondary" onclick="clearHistoryDateFilter()">清除日期筛选</button>`;
                } else if (hasKeyword) {
                    emptyMsg = `未找到包含 "<strong>${escapeHtml(historyKeyword)}</strong>" 的记录`;
                    emptyHint = '请尝试更换关键词，或清除搜索后查看全部记录。';
                    emptyAction = `<button class="btn btn-sm btn-outline-secondary" onclick="onHistorySearch('');document.getElementById('history-search').value='';">清除搜索</button>`;
                } else if (hasDateFilter) {
                    emptyMsg = '在指定日期范围内没有推送记录';
                    emptyHint = '请尝试调整日期范围。';
                    emptyAction = `<button class="btn btn-sm btn-outline-secondary" onclick="clearHistoryDateFilter()">清除日期筛选</button>`;
                }
                tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state">
                    <div class="empty-state__icon"><i class="fas fa-inbox" aria-hidden="true"></i></div>
                    <div class="empty-state__title">${emptyMsg}</div>
                    <div class="empty-state__desc">${emptyHint}</div>
                    <div class="empty-state__action">${emptyAction}</div>
                </div></td></tr>`;
                return;
            }

            tbody.innerHTML = '';
            history.forEach((item, index) => {
                const row = document.createElement('tr');

                // 失败记录用 class（消灭内联 backgroundColor）
                if (!item.success) {
                    row.classList.add('row-failed');
                }

                const successBadge = item.success ?
                    '<span class="badge bg-success" aria-label="推送成功"><i class="fas fa-check me-1" aria-hidden="true"></i>成功</span>' :
                    '<span class="badge bg-danger" aria-label="推送失败"><i class="fas fa-times me-1" aria-hidden="true"></i>失败</span>';

                // 来源标签
                const sourceBadge = item.source === 'backup' ?
                    '<span class="badge bg-warning text-dark" aria-label="来源：备份监控"><i class="fas fa-database me-1" aria-hidden="true"></i>备份</span>' :
                    '<span class="badge bg-info" aria-label="来源：日志监控"><i class="fas fa-file-alt me-1" aria-hidden="true"></i>日志</span>';

                // 使用 preview 字段，并高亮关键词
                const rawPreview = item.preview ||
                    (item.content ? (item.content.length > 100 ? item.content.substring(0, 97) + '...' : item.content) : '无内容');
                const previewHtml = highlightKeyword(escapeHtml(rawPreview), historyKeyword);

                // 格式化时间
                const timestamp = new Date(item.timestamp);
                const formattedTime = timestamp.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false
                });

                // 渲染渠道列（显示成功/失败图标）
                let channelHtml = '<span class="text-muted">-</span>';
                if (item.channel_results && Object.keys(item.channel_results).length > 0) {
                    const channelBadges = [];
                    for (const [ch, result] of Object.entries(item.channel_results)) {
                        const iconMap = {
                            'webhook': 'fa-link',
                            'wecom': 'fa-weixin',
                            'dingtalk': 'fa-comment',
                            'feishu': 'fa-paper-plane',
                            'bark': 'fa-mobile-alt',
                            'pushplus': 'fa-plus'
                        };
                        const icon = iconMap[ch] || 'fa-paper-plane';
                        const statusClass = result ? 'bg-success' : 'bg-danger';
                        const statusIcon = result ? 'fa-check' : 'fa-times';
                        channelBadges.push(`<span class="badge ${statusClass} me-1" title="${ch}: ${result ? '成功' : '失败'}"><i class="fas ${icon} me-1"></i><i class="fas ${statusIcon}"></i></span>`);
                    }
                    channelHtml = channelBadges.join('');
                }

                row.innerHTML = `
                    <td>
                        <div class="time-cell">
                            <i class="fas fa-clock me-1 text-primary"></i>
                            ${formattedTime}
                        </div>
                    </td>
                    <td>${sourceBadge}</td>
                    <td>${successBadge}</td>
                    <td>${channelHtml}</td>
                    <td style="white-space: nowrap;">
                        <span class="badge bg-primary rounded-pill">
                            ${item.count}
                        </span>
                    </td>
                    <td>
                        <code>${item.last_id || '-'}</code>
                    </td>
                    <td>
                        <div class="preview-content" data-content="${escapeHtml(item.content || '')}" onclick="showHistoryDetail(${index})">
                            <i class="fas fa-info-circle me-1 text-info"></i>
                            ${previewHtml}
                        </div>
                    </td>
                `;

                tbody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('加载历史失败:', error);
            const tbody = document.getElementById('history-table');
            tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state">
                <div class="empty-state__icon"><i class="fas fa-wifi" aria-hidden="true"></i></div>
                <div class="empty-state__title">网络请求失败</div>
                <div class="empty-state__desc">无法连接到服务器，请检查网络后重试。</div>
                <div class="empty-state__action"><button class="btn btn-sm btn-outline-primary" onclick="loadHistory()"><i class="fas fa-redo me-1"></i>重新加载</button></div>
            </div></td></tr>`;
            updatePaginationControls(0);
        });
}

// 更新分页控制按钮
function updatePaginationControls(total) {
    const prevBtn = document.getElementById('btn-prev-page');
    const nextBtn = document.getElementById('btn-next-page');
    const pageInfo = document.getElementById('history-page-info');
    const totalInfo = document.getElementById('history-total-info');

    if (!prevBtn || !nextBtn || !pageInfo || !totalInfo) return;

    // 计算总页数
    const totalPages = Math.ceil(total / historyPageSize) || 1;

    // 如果当前页超出范围，调整到最后一页
    if (historyCurrentPage > totalPages && totalPages > 0) {
        historyCurrentPage = totalPages;
    }

    // 更新页码显示（底部分页控件）
    pageInfo.textContent = `${historyCurrentPage}`;
    totalInfo.textContent = `${total}`;

    // 更新按钮状态
    prevBtn.disabled = historyCurrentPage <= 1;
    nextBtn.disabled = historyCurrentPage >= totalPages;
}

// 上一页
function prevPage() {
    if (historyCurrentPage > 1) {
        historyCurrentPage--;
        loadHistory();
    }
}

// 下一页
function nextPage() {
    const totalPages = Math.ceil(historyTotal / historyPageSize) || 1;
    if (historyCurrentPage < totalPages) {
        historyCurrentPage++;
        loadHistory();
    }
}

// 显示推送历史详情
function showHistoryDetail(historyId) {
    const modal = new bootstrap.Modal(document.getElementById('historyDetailModal'));
    const contentDiv = document.getElementById('historyDetailContent');

    // 显示加载中
    contentDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
        </div>
    `;
    modal.show();

    // 获取详情数据
    apiFetch(`/api/history/${historyId}`)
        .then(response => response.json())
        .then(result => {
            if (result.success && result.data) {
                const data = result.data;
                const timestamp = new Date(data.timestamp);
                const formattedTime = timestamp.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false
                });

                const successBadge = data.success ?
                    '<span class="badge bg-success" aria-label="推送成功"><i class="fas fa-check me-1" aria-hidden="true"></i>成功</span>' :
                    '<span class="badge bg-danger" aria-label="推送失败"><i class="fas fa-times me-1" aria-hidden="true"></i>失败</span>';

                // 构建详情内容
                let levelsHtml = '';
                if (data.levels) {
                    levelsHtml = `
                        <div class="mt-3">
                            <h6 class="text-primary"><i class="fas fa-layer-group me-2"></i>日志级别统计</h6>
                            <div class="d-flex flex-wrap gap-2">
                                ${Object.entries(data.levels).map(([level, count]) => `
                                    <span class="badge bg-info">${level}: ${count}</span>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }

                // 构建渠道推送结果
                let channelResultsHtml = '';
                if (data.channel_results && Object.keys(data.channel_results).length > 0) {
                    const iconMap = {
                        'webhook': 'fa-link',
                        'wecom': 'fa-weixin',
                        'dingtalk': 'fa-comment',
                        'feishu': 'fa-paper-plane',
                        'bark': 'fa-mobile-alt',
                        'pushplus': 'fa-plus'
                    };
                    const channelRows = Object.entries(data.channel_results).map(([ch, result]) => {
                        const icon = iconMap[ch] || 'fa-paper-plane';
                        const statusClass = result ? 'text-success' : 'text-danger';
                        const statusIcon = result ? 'fa-check-circle' : 'fa-times-circle';
                        return `<tr><td><i class="fas ${icon} me-2"></i>${ch}</td><td class="${statusClass}"><i class="fas ${statusIcon} me-1"></i>${result ? '成功' : '失败'}</td></tr>`;
                    }).join('');
                    channelResultsHtml = `
                        <div class="mt-3">
                            <h6 class="text-primary"><i class="fas fa-paper-plane me-2"></i>推送渠道结果</h6>
                            <table class="table table-sm table-bordered">
                                ${channelRows}
                            </table>
                        </div>
                    `;
                }

                contentDiv.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <div class="card mb-3">
                                <div class="card-body">
                                    <h6 class="text-muted mb-3"><i class="fas fa-info-circle me-2"></i>基本信息</h6>
                                    <table class="table table-sm mb-0">
                                                <tr>
                                                    <td width="30%">推送时间</td>
                                                    <td><strong>${formattedTime}</strong></td>
                                                </tr>
                                                <tr>
                                                    <td>推送状态</td>
                                                    <td>${successBadge}</td>
                                                </tr>
                                                <tr>
                                                    <td>日志数量</td>
                                                    <td><span class="badge bg-primary rounded-pill">${data.count}</span> 条</td>
                                                </tr>
                                                <tr>
                                                    <td>最后日志ID</td>
                                                    <td><code>${data.last_id || '-'}</code></td>
                                                </tr>
                                            </table>
                                        </div>
                                    </div>
                                    ${channelResultsHtml}
                                </div>
                                <div class="col-md-6">
                                    <div class="card mb-3">
                                        <div class="card-body">
                                            <h6 class="text-muted mb-3"><i class="fas fa-eye me-2"></i>预览信息</h6>
                                            <div class="alert alert-info mb-0" style="max-height: 200px; overflow-y: auto;">
                                                <pre style="margin: 0; white-space: pre-wrap; word-break: break-word;">${escapeHtml(data.preview || '无预览')}</pre>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            ${levelsHtml}
                            <div class="card">
                                <div class="card-header bg-light">
                                    <h6 class="mb-0"><i class="fas fa-file-alt me-2"></i>完整推送内容</h6>
                                </div>
                                <div class="card-body">
                                    <div style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 14px; white-space: pre-wrap; word-break: break-word;">
                                        ${escapeHtml(data.content || '无内容')}
                                    </div>
                                </div>
                            </div>
                        `;
                    } else {
                        contentDiv.innerHTML = `
                            <div class="alert alert-danger">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                ${result.message || '加载失败'}
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    console.error('获取历史详情失败:', error);
                    contentDiv.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            获取详情失败: ${error.message}
                        </div>
                    `;
                });
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 刷新历史
function refreshHistory() {
    historyCurrentPage = 1;  // 重置到第一页
    loadHistory();
}

// 检查数据库状态
// 检查数据库状态（合并版：同时检查数据库信息和连接状态）
function checkDatabaseFull() {
    const panel = document.getElementById('db-status-panel');
    panel.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin me-2"></i>正在检查数据库...</div>';
    
    // 同时发起四个检查请求：日志数据库详情、日志数据库连接状态、备份数据库状态、备份数据库统计
    Promise.all([
        apiFetch('/api/check-db').then(r => r.json()).catch(() => ({ success: false, error: '请求失败' })),
        apiFetch('/api/db-check').then(r => r.json()).catch(() => ({ success: false, error: '请求失败' })),
        apiFetch('/api/backup/status').then(r => r.json()).catch(() => ({})),
        apiFetch('/api/backup/statistics').then(r => r.json()).catch(() => ({}))
    ])
    .then(([dbData, connData, backupStatusData, backupData]) => {
        let html = '';

        // 更新最后备份时间
        const lastBackupTimeEl = document.getElementById('last-backup-time');
        if (lastBackupTimeEl) {
            lastBackupTimeEl.textContent = (backupStatusData.last_backup_time || backupStatusData.last_finished_time) || '-';
        }
        
        // 数据库详情部分
        if (dbData.success) {
            const newEventsHTML = dbData.new_event_count > 0 ?
                `<div class="alert alert-warning mt-3">
                    <h6 class="alert-heading"><i class="fas fa-exclamation-triangle me-2"></i>发现 ${dbData.new_event_count} 个新事件ID</h6>
                    <hr>
                    <div class="db-status" style="max-height: 200px; overflow-y: auto;">
                        ${dbData.new_event_ids.map(id => `<code class="d-block mb-1">${id}</code>`).join('')}
                    </div>
                    <div class="mt-2">
                        <small class="text-muted">
                            <i class="fas fa-info-circle me-1"></i>
                            这些事件ID在配置文件中不存在，建议更新配置
                        </small>
                    </div>
                </div>` :
                `<div class="alert alert-success mt-3">
                    <i class="fas fa-check-circle me-2"></i>没有新的事件ID，所有事件都在配置中
                </div>`;
            
            html += `
                <div class="alert alert-info">
                    <i class="fas fa-database me-2"></i>数据库详情
                </div>
                
                <div class="row mt-3">
                    <div class="col-md-6">
                        <h6 class="mb-3"><i class="fas fa-chart-bar me-2"></i>日志数据库统计</h6>
                        <div class="db-status">
                            <i class="fas fa-database me-2"></i>总记录数: ${dbData.total_records}<br>
                            <i class="fas fa-hashtag me-2"></i>监控最后日志ID: ${dbData.monitor_last_id}<br>
                            <i class="fas fa-clock me-2"></i>最近记录数: ${dbData.recent_records_count}<br>
                            <i class="fas fa-tags me-2"></i>已知事件数: ${dbData.total_known_events}<br>
                            <i class="fas fa-folder me-2"></i>数据库事件数: ${dbData.total_events_in_db}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="mb-3"><i class="fas fa-database me-2"></i>备份数据库统计</h6>
                        <div class="db-status">
                            ${(backupData.total_tasks > 0 || backupData.total_operations > 0) ? `
                                <i class="fas fa-tasks me-2"></i>任务总数: ${backupData.total_tasks}<br>
                                <i class="fas fa-list me-2"></i>操作总数: ${backupData.total_operations}<br>
                                <i class="fas fa-clock me-2"></i>24小时内: ${backupData.recent_operations_count}<br>
                                <i class="fas fa-history me-2"></i>最新时间: ${backupData.last_backup_time || backupData.last_operation_time || '无'}
                            ` : '<span class="text-muted">暂无数据</span>'}
                        </div>
                    </div>
                </div>
                
                ${newEventsHTML}
            `;
        } else {
            html += `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>数据库详情获取失败: ${dbData.error}
                </div>
            `;
        }
        
        panel.innerHTML = html;
    })
    .catch(error => {
        panel.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-times-circle me-2"></i>检查失败: ${error.message}
            </div>
        `;
    });
}

// 保留checkDatabase别名用于启动时调用
function checkDatabase() {
    return checkDatabaseFull();
}

// 显示通知
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} mb-0 js-toast`;

    // 主题适配：为所有 5 个主题定义颜色方案
    const currentTheme = ThemeManager.getCurrentTheme();

    // 主题颜色映射：根据主题类型和通知类型定义对应的半透明背景色
    const themeColors = {
        default: {
            success: { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.45)',  color: '#d1fae5' },
            danger:  { bg: 'rgba(239,68,68,0.18)',   border: 'rgba(239,68,68,0.45)',   color: '#fde8e8' },
            warning: { bg: 'rgba(245,158,11,0.18)',  border: 'rgba(245,158,11,0.45)',  color: '#fef3c7' },
            info:    { bg: 'rgba(59,130,246,0.18)',  border: 'rgba(59,130,246,0.45)',  color: '#dbeafe' },
        },
        dark: {
            success: { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.45)',  color: '#d1fae5' },
            danger:  { bg: 'rgba(239,68,68,0.18)',   border: 'rgba(239,68,68,0.45)',   color: '#fde8e8' },
            warning: { bg: 'rgba(245,158,11,0.18)',  border: 'rgba(245,158,11,0.45)',  color: '#fef3c7' },
            info:    { bg: 'rgba(59,130,246,0.18)',  border: 'rgba(59,130,246,0.45)',  color: '#dbeafe' },
        },
        ocean: {
            success: { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.45)',  color: '#d1fae5' },
            danger:  { bg: 'rgba(239,68,68,0.18)',   border: 'rgba(239,68,68,0.45)',   color: '#fde8e8' },
            warning: { bg: 'rgba(245,158,11,0.18)',  border: 'rgba(245,158,11,0.45)',  color: '#fef3c7' },
            info:    { bg: 'rgba(59,130,246,0.18)',  border: 'rgba(59,130,246,0.45)',  color: '#dbeafe' },
        },
        green: {
            success: { bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.35)',  color: '#065f46' },
            danger:  { bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.35)',   color: '#7f1d1d' },
            warning: { bg: 'rgba(245,158,11,0.12)',  border: 'rgba(245,158,11,0.35)',  color: '#78350f' },
            info:    { bg: 'rgba(59,130,246,0.12)',  border: 'rgba(59,130,246,0.35)',  color: '#1e40af' },
        },
        sunset: {
            success: { bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.35)',  color: '#064e3b' },
            danger:  { bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.35)',   color: '#7f1d1d' },
            warning: { bg: 'rgba(245,158,11,0.12)',  border: 'rgba(245,158,11,0.35)',  color: '#92400e' },
            info:    { bg: 'rgba(59,130,246,0.12)',  border: 'rgba(59,130,246,0.35)',  color: '#1e3a8a' },
        },
    };

    const colors = themeColors[currentTheme]?.[type] || themeColors.default[type];
    // 使用 background 简写属性而非 background-color，避免被 CSS 的 background 简写覆盖
    // 格式：background: <background-color> <background-image> <background-position> ...
    // 这里只设置背景色，其他属性保持默认
    let extraStyle = '';
    if (colors) {
        extraStyle = `background:${colors.bg} !important; border-color:${colors.border} !important; color:${colors.color} !important;`;
    }

    notification.style.cssText = `position:fixed; top:20px; right:20px; min-width:300px; animation:slideIn 0.3s ease-out; ${extraStyle}`;

    // 根据类型设置图标
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'warning') icon = 'fa-exclamation-triangle';
    if (type === 'danger') icon = 'fa-times-circle';

    // 亮色系主题（green / sunset）的关闭按钮无需反色，深色系主题需要
    const darkThemes = ['dark', 'ocean'];
    const isDark = darkThemes.includes(currentTheme);
    const closeBtnStyle = isDark ? 'filter:invert(1) grayscale(100%) brightness(200%);' : '';
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas ${icon} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close ms-auto" style="${closeBtnStyle}" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    // 添加到页面
    document.body.appendChild(notification);

    // 3秒后自动消失
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 绘制饼状图


// 控制监控程序
function controlMonitor(action) {
    apiFetch('/api/control', {
        credentials: 'same-origin', method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
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

// ========== 浮动按钮菜单和面板切换函数 ==========

// 切换浮动按钮菜单收缩/展开
function toggleFabMenu() {
    const fabMenu = document.getElementById('fabMenu');
    const mainBtnIcon = fabMenu.querySelector('.fab-main i');

    fabMenu.classList.toggle('active');

    // 根据菜单状态切换图标
    if (fabMenu.classList.contains('active')) {
        mainBtnIcon.classList.remove('fa-bars');
        mainBtnIcon.classList.add('fa-times');
        fabMenu.querySelector('.fab-main').setAttribute('title', '收起菜单');
    } else {
        mainBtnIcon.classList.remove('fa-times');
        mainBtnIcon.classList.add('fa-bars');
        fabMenu.querySelector('.fab-main').setAttribute('title', '展开菜单');
    }
}

// 显示/隐藏用户菜单
function showUserMenu() {
    const menu = document.getElementById('userMenuPopup');
    menu.classList.toggle('active');
}

function hideUserMenu() {
    const menu = document.getElementById('userMenuPopup');
    menu.classList.remove('active');
}

// 切换可展开操作菜单
function toggleExpandableMenu() {
    const menu = document.getElementById('expandableMenu');
    menu.classList.toggle('active');
}

// 点击外部关闭弹窗菜单
document.addEventListener('click', function(e) {
    // 关闭用户菜单
    const userMenu = document.getElementById('userMenuPopup');
    const userBtn = document.querySelector('.fab-btn-user');
    if (userMenu && userBtn && !userMenu.contains(e.target) && !userBtn.contains(e.target)) {
        userMenu.classList.remove('active');
    }
    // 关闭操作菜单
    const opMenu = document.getElementById('expandableMenu');
    const opBtn = document.querySelector('.expand-btn');
    if (opMenu && opBtn && !opMenu.contains(e.target) && !opBtn.contains(e.target)) {
        opMenu.classList.remove('active');
    }
});

// 切换面板显示（不收起按钮组）
function switchFabPanel(element, target) {
    // 停止健康检查的实时更新（如果正在运行）
    stopHealthUpdate();

    // 更新按钮激活状态
    document.querySelectorAll('.fab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    element.classList.add('active');

    // 更新面板显示
    document.querySelectorAll('.config-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById('panel-' + target).classList.add('active');

    // 如果切换到数据库面板，自动加载数据库状态
    if (target === 'dbstatus') {
        checkDatabaseFull();
    }

    // 如果切换到健康检查面板，先加载健康状态，然后开始实时更新
    if (target === 'health') {
        // 先加载健康状态数据
        loadHealthStatus();
        // 延迟1秒后开始实时更新，确保DOM元素已创建
        setTimeout(() => {
            startHealthUpdate();
        }, 1000);
    }
}

// 保留旧函数兼容性
function toggleSidebar() {
    toggleFabMenu();
}

function switchConfigPanel(element, target) {
    const targetBtn = document.querySelector(`.fab-btn[data-target="${target}"]`);
    if (targetBtn) {
        switchFabPanel(targetBtn, target);
    } else {
        // 移动端：fab-btn 可能不存在，直接切换面板并更新移动端导航激活状态
        stopHealthUpdate();
        document.querySelectorAll('.config-panel').forEach(panel => panel.classList.remove('active'));
        const panel = document.getElementById('panel-' + target);
        if (panel) panel.classList.add('active');
        // 同步移动端底部导航激活状态
        document.querySelectorAll('.mobile-nav-btn').forEach(btn => btn.classList.remove('active'));
        const mobileBtn = document.querySelector(`.mobile-nav-btn[data-target="${target}"]`);
        if (mobileBtn) mobileBtn.classList.add('active');
        // 特殊面板初始化
        if (target === 'dbstatus') checkDatabaseFull();
        if (target === 'health') { loadHealthStatus(); setTimeout(() => startHealthUpdate(), 1000); }
    }
}

// 切换密码显示/隐藏
function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    const icon = button.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// 显示确认模态框
function showConfirmModal(message, onConfirm) {
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    document.getElementById('confirmModalMessage').textContent = message;
    
    const confirmButton = document.getElementById('confirmModalConfirm');
    
    // 移除之前的事件监听器
    const newConfirmButton = confirmButton.cloneNode(true);
    confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton);
    
    // 添加新的事件监听器
    newConfirmButton.addEventListener('click', function() {
        modal.hide();
        if (onConfirm) {
            onConfirm();
        }
    });
    
    modal.show();
}

// 重置监控
function resetMonitor() {
    showConfirmModal('确定要重置监控吗？这将从数据库中重新读取最后日志ID和最后备份时间作为监控的起点。', function() {
        controlMonitor('reset_monitor');
    });
}

// 全选某个分类的所有事件
function selectAllInCategory(category) {
    document.querySelectorAll(`.category-${category}`).forEach(checkbox => {
        checkbox.checked = true;
    });
}

// 全不选某个分类的所有事件
function deselectAllInCategory(category) {
    document.querySelectorAll(`.category-${category}`).forEach(checkbox => {
        checkbox.checked = false;
    });
}

// 测试Webhook
function testWebhook() {
    showConfirmModal('确定发送测试推送消息吗？', function() {
        apiFetch('/api/test-webhook', {
            credentials: 'same-origin', method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                NotificationManager.success('测试推送成功', '测试推送成功！');
            } else {
                NotificationManager.error('测试推送失败', '测试推送失败！');
            }
            loadHistory();
        });
    });
}

// ========== 独立保存配置函数 ==========

// 保存日志监控设置
function saveBasicConfig() {
    // 获取选中的日志级别
    const selectedLevels = [];
    document.querySelectorAll('#log-levels input[type="checkbox"]:checked').forEach(checkbox => {
        selectedLevels.push(checkbox.value);
    });

    // 获取事件ID列表
    const allEventInputs = document.querySelectorAll('#event-types input[type="checkbox"]:not(.push-checkbox)');
    const selectedEvents = [];

    allEventInputs.forEach(checkbox => {
        // 事件 checkbox: 决定是否监控该事件（选中=推送）
        if (checkbox.checked) {
            selectedEvents.push(checkbox.value);
        }
    });

    const newConfig = {
        database_path: document.getElementById('database-path').value,
        check_interval: parseInt(document.getElementById('check-interval-input').value),
        selected_levels: selectedLevels,
        selected_events: selectedEvents,
        log_levels: currentConfig.log_levels || ["调试", "普通", "警告", "错误", "严重错误"],
        event_ids: currentConfig.event_ids || []
    };

    // 获取现有配置，保留其他设置
    apiFetch('/api/config')
        .then(response => response.json())
        .then(currentConfig => {
            const mergedConfig = { ...currentConfig, ...newConfig };
            return apiFetch('/api/config', {
                credentials: 'same-origin', method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mergedConfig)
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                NotificationManager.success('保存成功', '日志监控设置已保存！');
                loadStatus();
                checkDatabase();
                if (newConfig.database_path) {
                    setTimeout(() => checkDatabaseConnection(), 1000);
                }
            } else {
                NotificationManager.error('保存失败', '保存失败！' + (data.error || ''));
            }
        })
        .catch(error => {
            console.error('保存日志监控设置时出错:', error);
            NotificationManager.error('保存错误', '保存日志监控设置时出错: ' + error.message);
        });
}

// 保存推送配置
function savePushConfig() {
    const newConfig = {
        webhook_url: document.getElementById('webhook-url').value,
        push_channels: {
            webhook: document.getElementById('push-webhook-enabled').checked,
            wecom: document.getElementById('push-wecom-enabled').checked,
            dingtalk: document.getElementById('push-dingtalk-enabled').checked,
            feishu: document.getElementById('push-feishu-enabled').checked,
            bark: document.getElementById('push-bark-enabled').checked,
            pushplus: document.getElementById('push-pushplus-enabled').checked,
            meow: document.getElementById('push-meow-enabled').checked
        },
        wecom: {
            enabled: document.getElementById('push-wecom-enabled').checked,
            webhook_url: document.getElementById('wecom-webhook-url').value
        },
        dingtalk: {
            enabled: document.getElementById('push-dingtalk-enabled').checked,
            webhook_url: document.getElementById('dingtalk-webhook-url').value,
            secret: document.getElementById('dingtalk-secret').value
        },
        feishu: {
            enabled: document.getElementById('push-feishu-enabled').checked,
            webhook_url: document.getElementById('feishu-webhook-url').value
        },
        bark: {
            enabled: document.getElementById('push-bark-enabled').checked,
            device_key: document.getElementById('bark-device-key').value,
            server: document.getElementById('bark-server').value || 'https://api.day.app'
        },
        pushplus: {
            enabled: document.getElementById('push-pushplus-enabled').checked,
            token: document.getElementById('pushplus-token').value,
            topic: document.getElementById('pushplus-topic').value
        },
        meow: {
            enabled: document.getElementById('push-meow-enabled').checked,
            nickname: document.getElementById('meow-nickname').value,
            title: document.getElementById('meow-title').value,
            msgtype: document.getElementById('meow-msgtype').value
        },
        do_not_disturb: {
            enabled: document.getElementById('dnd-enabled').checked,
            start_time: document.getElementById('dnd-start-time').value,
            end_time: document.getElementById('dnd-end-time').value
        },
        alert_aggregation: {
            enabled: document.getElementById('alert-agg-enabled').checked,
            window_seconds: parseInt(document.getElementById('alert-agg-window').value) || 300,
            threshold: parseInt(document.getElementById('alert-agg-threshold').value) || 5,
            silence_seconds: parseInt(document.getElementById('alert-agg-silence').value) || 600
        }
    };

    apiFetch('/api/config')
        .then(response => response.json())
        .then(currentConfig => {
            const mergedConfig = { ...currentConfig, ...newConfig };
            return apiFetch('/api/config', {
                credentials: 'same-origin', method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mergedConfig)
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                NotificationManager.success('保存成功', '推送配置已保存！');
                loadStatus();
                // 保存成功后刷新聚合统计
                setTimeout(() => loadAggStats(), 600);
            } else {
                NotificationManager.error('保存失败', '保存失败！' + (data.error || ''));
            }
        })
        .catch(error => {
            console.error('保存推送配置时出错:', error);
            NotificationManager.error('保存错误', '保存推送配置时出错: ' + error.message);
        });
}

// 保存推送筛选
function saveFilterConfig() {
    const selectedLevels = [];
    document.querySelectorAll('#log-levels input[type="checkbox"]:checked').forEach(checkbox => {
        selectedLevels.push(checkbox.value);
    });

    const allEventInputs = document.querySelectorAll('#event-types input[type="checkbox"]:not(.push-checkbox)');
    const selectedEvents = [];

    allEventInputs.forEach(checkbox => {
        // 事件 checkbox: 决定是否监控该事件（选中=推送）
        if (checkbox.checked) {
            selectedEvents.push(checkbox.value);
        }
    });

    const newConfig = {
        selected_levels: selectedLevels,
        selected_events: selectedEvents,
        log_levels: currentConfig.log_levels || ["调试", "普通", "警告", "错误", "严重错误"],
        event_ids: currentConfig.event_ids || []
    };

    apiFetch('/api/config')
        .then(response => response.json())
        .then(currentConfig => {
            const mergedConfig = { ...currentConfig, ...newConfig };
            return apiFetch('/api/config', {
                credentials: 'same-origin', method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mergedConfig)
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                NotificationManager.success('保存成功', '推送筛选已保存！');
                loadStatus();
            } else {
                NotificationManager.error('保存失败', '保存失败！' + (data.error || ''));
            }
        })
        .catch(error => {
            console.error('保存推送筛选时出错:', error);
            NotificationManager.error('保存错误', '保存推送筛选时出错: ' + error.message);
        });
}

// 保存主题设置
function saveThemeConfig() {
    const newConfig = {
        theme: document.querySelector('input[name="theme"]:checked')?.value || 'default'
    };

    apiFetch('/api/config')
        .then(response => response.json())
        .then(currentConfig => {
            const mergedConfig = { ...currentConfig, ...newConfig };
            return apiFetch('/api/config', {
                credentials: 'same-origin', method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mergedConfig)
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                NotificationManager.success('保存成功', '主题设置已保存！');
                ThemeManager.setTheme(newConfig.theme);
                loadStatus();
            } else {
                NotificationManager.error('保存失败', '保存失败！' + (data.error || ''));
            }
        })
        .catch(error => {
            console.error('保存主题设置时出错:', error);
            NotificationManager.error('保存错误', '保存主题设置时出错: ' + error.message);
        });
}

// 保存备份监控配置
function saveBackupConfig() {
    const newConfig = {
        backup_monitor: {
            enabled: document.getElementById('backup-monitor-enabled').checked,
            database_path: document.getElementById('backup-db-path').value,
            check_interval: parseInt(document.getElementById('backup-check-interval').value) || 10,
            status_filter: [1, 2, 3, 4].filter(i =>
                document.getElementById('backup-status-' + i)?.checked
            )
        }
    };

    apiFetch('/api/config')
        .then(response => response.json())
        .then(currentConfig => {
            const mergedConfig = { ...currentConfig, backup_monitor: newConfig.backup_monitor };
            return apiFetch('/api/config', {
                credentials: 'same-origin', method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mergedConfig)
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                NotificationManager.success('保存成功', '备份监控配置已保存！');
                loadStatus();
            } else {
                NotificationManager.error('保存失败', '保存失败！' + (data.error || ''));
            }
        })
        .catch(error => {
            console.error('保存备份监控配置时出错:', error);
            NotificationManager.error('保存错误', '保存备份监控配置时出错: ' + error.message);
        });
}

// ========== 备份监控相关函数 ==========

// 测试备份数据库连接
function testBackupDbConnection() {
    const dbPath = document.getElementById('backup-db-path').value;
    if (!dbPath) {
        alert('请输入备份数据库路径');
        return;
    }

    apiFetch('/api/backup/test-connection', {
        credentials: 'same-origin', method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ database_path: dbPath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('连接成功！\n' + data.message);
        } else {
            alert('连接失败：' + data.message);
        }
    })
    .catch(error => {
        alert('测试连接时出错: ' + error.message);
    });
}

// ========== 认证相关函数 ==========

// 简化版：不再做前端重定向，依赖后端session控制
async function checkSession() {
    try {
        const response = await apiFetch('/api/auth/check-session', {
            credentials: 'same-origin',
            cache: 'no-store'
        });
        
        const data = await response.json();

        if (data.logged_in === true) {
            // 已登录，显示用户名
            const username = data.username;
            const usernameEl = document.getElementById('current-username');
            const popupUsernameEl = document.getElementById('popup-username');
            if (usernameEl) usernameEl.textContent = username;
            if (popupUsernameEl) popupUsernameEl.textContent = username;
            console.log('会话有效，用户:', username);
        } else {
            // Session无效，跳转到登录页
            console.log('会话无效，跳转到登录页');
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('检查会话失败:', error);
        window.location.href = '/login';
    }
}

async function logout() {
    if (!confirm('确定要退出吗？')) {
        return;
    }

    try {
        const response = await apiFetch('/api/auth/logout', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            // 清除所有浏览器存储
            sessionStorage.clear();
            localStorage.clear();
            // 强制刷新到登录页（加时间戳避免缓存）
            window.location.href = '/login?t=' + Date.now();
        } else {
            alert('退出失败');
        }
    } catch (error) {
        console.error('退出失败:', error);
        // 即使出错也尝试跳转
        window.location.href = '/login?t=' + Date.now();
    }
}

function showChangePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'block';
    document.getElementById('changePasswordModal').classList.add('show');
}

function hideChangePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'none';
    document.getElementById('changePasswordModal').classList.remove('show');
    // 清空表单
    document.getElementById('oldPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmNewPassword').value = '';
    document.getElementById('changePasswordAlert').innerHTML = '';
}

async function changePassword() {
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmNewPassword = document.getElementById('confirmNewPassword').value;

    // 清除之前的提示
    document.getElementById('changePasswordAlert').innerHTML = '';

    // 验证输入
    if (!oldPassword || !newPassword || !confirmNewPassword) {
        showChangePasswordAlert('请填写所有字段', 'danger');
        return;
    }

    if (newPassword.length < 6) {
        showChangePasswordAlert('新密码至少需要6个字符', 'danger');
        return;
    }

    if (newPassword !== confirmNewPassword) {
        showChangePasswordAlert('两次输入的新密码不一致', 'danger');
        return;
    }

    try {
        const response = await apiFetch('/api/auth/change-password', {
            credentials: 'same-origin', method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (data.success) {
            showChangePasswordAlert(data.message, 'success');
            // 2秒后关闭模态框
            setTimeout(() => {
                hideChangePasswordModal();
            }, 2000);
        } else {
            showChangePasswordAlert(data.error || '密码修改失败', 'danger');
        }
    } catch (error) {
        console.error('修改密码失败:', error);
        showChangePasswordAlert('网络错误，请稍后重试', 'danger');
    }
}

function showChangePasswordAlert(message, type) {
    const alertContainer = document.getElementById('changePasswordAlert');
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} me-2"></i>
            ${message}
        </div>
    `;
    alertContainer.innerHTML = alertHTML;
}

// ========== 告警聚合统计 ==========

/**
 * 拉取 /api/alert-aggregation/stats，更新推送配置面板内的统计条。
 * 若聚合功能未启用则隐藏统计条。
 */
function loadAggStats() {
    apiFetch('/api/alert-aggregation/stats')
        .then(r => r.json())
        .then(data => {
            if (data.error) return;

            const bar = document.getElementById('alert-agg-stats-bar');
            const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

            if (data.enabled) {
                if (bar) bar.style.display = '';
                setEl('agg-stat-total',      data.total_received   ?? 0);
                setEl('agg-stat-passed',     data.total_pushed     ?? 0);
                setEl('agg-stat-suppressed', data.total_suppressed ?? 0);
                setEl('agg-stat-silenced',   data.total_silenced   ?? 0);
                setEl('agg-stat-groups',     data.active_groups    ?? 0);
            } else {
                if (bar) bar.style.display = 'none';
            }
        })
        .catch(err => console.warn('加载告警聚合统计失败:', err));
}

// ========== 自动刷新功能 ==========
let autoRefreshInterval = null;
const DEFAULT_REFRESH_INTERVAL = 10000; // 10秒

function toggleAutoRefresh(enabled) {
    if (enabled) {
        startAutoRefresh();
        NotificationManager.info('已开启自动刷新', '数据将每10秒自动更新');
    } else {
        stopAutoRefresh();
        NotificationManager.info('已关闭自动刷新', '需要手动刷新数据');
    }
    // 保存设置到本地存储
    localStorage.setItem('autoRefreshEnabled', enabled);
}

function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    autoRefreshInterval = setInterval(() => {
        if (document.getElementById('auto-refresh-toggle')?.checked) {
            loadStatus();
        }
    }, DEFAULT_REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// 初始化自动刷新状态
function initAutoRefresh() {
    const saved = localStorage.getItem('autoRefreshEnabled');
    const toggle = document.getElementById('auto-refresh-toggle');
    if (toggle) {
        // 默认开启
        const enabled = saved === null ? true : saved === 'true';
        toggle.checked = enabled;
        if (enabled) {
            startAutoRefresh();
        }
    }
}

// ========== 历史记录日期筛选功能 ==========
let historyDateFilter = {
    startDate: null,
    endDate: null
};

function onHistoryDateFilter() {
    const startDate = document.getElementById('history-date-start')?.value;
    const endDate = document.getElementById('history-date-end')?.value;

    historyDateFilter.startDate = startDate || null;
    historyDateFilter.endDate = endDate || null;

    // 重新加载历史记录
    if (typeof loadHistory === 'function') {
        loadHistory();
    }
}

function clearHistoryDateFilter() {
    document.getElementById('history-date-start').value = '';
    document.getElementById('history-date-end').value = '';
    historyDateFilter.startDate = null;
    historyDateFilter.endDate = null;

    if (typeof loadHistory === 'function') {
        loadHistory();
    }
}

// ========== KPI数字滚动动画 ==========
function animateNumber(element, newValue) {
    if (!element) return;

    const oldValue = element.textContent;
    if (oldValue === newValue) return;

    // 添加动画类
    element.classList.add('animating');

    // 更新数值
    element.textContent = newValue;

    // 动画结束后移除类
    setTimeout(() => {
        element.classList.remove('animating');
    }, 400);
}

// 初始化历史记录日期筛选默认值（前一天至当前）
function initHistoryDateFilter() {
    const startDateInput = document.getElementById('history-date-start');
    const endDateInput = document.getElementById('history-date-end');

    if (startDateInput && endDateInput) {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        // 格式化日期为 YYYY-MM-DD
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };

        // 设置默认值：前一天至今天
        startDateInput.value = formatDate(yesterday);
        endDateInput.value = formatDate(today);

        // 触发筛选以应用默认值
        onHistoryDateFilter();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initAutoRefresh();
    initHistoryDateFilter();
});