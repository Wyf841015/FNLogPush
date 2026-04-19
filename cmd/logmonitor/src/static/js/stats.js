// ========== stats.js - 统计模块 ==========

// ========== 图表实例 ==========
var pushTrendChart = null;
var pushChannelChart = null;
var currentTrendRange = '24h';

// ========== 告警聚合统计 ==========

function loadAggStats() {
    var container = document.getElementById('agg-stats-content');
    if (!container) return;
    
    container.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>';
    
    apiFetch('/api/agg/stats')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success && data.stats) {
                var stats = data.stats;
                container.innerHTML = '<div class="row">' +
                    '<div class="col-md-4 mb-3"><div class="card text-center"><div class="card-body">' +
                    '<h3 class="text-primary">' + (stats.total_log_events || 0) + '</h3>' +
                    '<p class="text-muted mb-0">总日志事件</p></div></div></div>' +
                    '<div class="col-md-4 mb-3"><div class="card text-center"><div class="card-body">' +
                    '<h3 class="text-success">' + (stats.total_pushed || 0) + '</h3>' +
                    '<p class="text-muted mb-0">总推送次数</p></div></div></div>' +
                    '<div class="col-md-4 mb-3"><div class="card text-center"><div class="card-body">' +
                    '<h3 class="text-warning">' + (stats.total_suppressed || 0) + '</h3>' +
                    '<p class="text-muted mb-0">被压制次数</p></div></div></div></div>';
            } else {
                container.innerHTML = '<div class="alert alert-info">暂无统计数据</div>';
            }
        })
        .catch(function(error) {
            container.innerHTML = '<div class="alert alert-danger">加载失败: ' + error.message + '</div>';
        });
}

// ========== ECharts 图表初始化 ==========

function initCharts() {
    // 只在图表未初始化时才初始化
    var trendDom = document.getElementById('push-trend-chart');
    if (trendDom && !pushTrendChart) {
        pushTrendChart = echarts.init(trendDom, null, { renderer: 'canvas' });
        window.addEventListener('resize', function() {
            if (pushTrendChart) pushTrendChart.resize();
            if (pushChannelChart) pushChannelChart.resize();
        });
    }
    
    // 只在图表未初始化时才初始化
    var channelDom = document.getElementById('push-channel-chart');
    if (channelDom && !pushChannelChart) {
        pushChannelChart = echarts.init(channelDom, null, { renderer: 'canvas' });
    }
}

function loadChartData() {
    loadPushTrendData();
    loadPushChannelData();
    loadStatsOverviewFromApi();
}

function loadPushTrendData() {
    if (!pushTrendChart) {
        console.log('[Stats] pushTrendChart not initialized');
        return;
    }
    
    pushTrendChart.showLoading({
        text: '加载中...',
        color: '#667eea',
        textColor: 'rgba(255,255,255,0.6)',
        maskColor: 'rgba(0,0,0,0.1)'
    });
    
    console.log('[Stats] Loading chart data from API...');
    
    // 使用新的统计API
    apiFetch('/api/stats/chart-data')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            console.log('[Stats] API response:', data);
            pushTrendChart.hideLoading();
            if (data.success) {
                var trendData = currentTrendRange === '24h' ? data.trend24h : data.trend7d;
                console.log('[Stats] Trend data:', trendData);
                if (trendData && trendData.length > 0) {
                    updatePushTrendChart(trendData);
                } else {
                    console.log('[Stats] No trend data, using mock');
                    updatePushTrendChart(generateMockTrendData());
                }
                // 更新概览统计
                if (data.overview) {
                    updateStatsOverview(data.overview);
                }
                // 更新渠道数据
                if (data.channels && data.channels.length > 0) {
                    updatePushChannelChart(data.channels);
                }
            } else {
                console.log('[Stats] API failed, using mock');
                updatePushTrendChart(generateMockTrendData());
            }
        })
        .catch(function(err) {
            console.error('[Stats] API error:', err);
            pushTrendChart.hideLoading();
            updatePushTrendChart(generateMockTrendData());
        });
}

function loadPushChannelData() {
    if (!pushChannelChart) return;
    
    // 渠道数据从统计API获取
}

// 从API加载统计概览
function loadStatsOverviewFromApi() {
    apiFetch('/api/stats/chart-data')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success && data.overview) {
                updateStatsOverview(data.overview);
            }
        })
        .catch(function() {});
}

// 更新统计概览
function updateStatsOverview(overview) {
    var totalEl = document.getElementById('stats-total-push');
    var todayEl = document.getElementById('stats-today-push');
    if (totalEl) totalEl.textContent = overview.total || 0;
    if (todayEl) todayEl.textContent = overview.today || 0;
}

function generateMockTrendData() {
    var data = [];
    var now = new Date();
    var i;
    
    if (currentTrendRange === '24h') {
        for (i = 23; i >= 0; i--) {
            var time = new Date(now);
            time.setHours(time.getHours() - i);
            data.push({
                push_time: time.toISOString(),
                count: Math.floor(Math.random() * 20) + 5
            });
        }
    } else {
        for (i = 6; i >= 0; i--) {
            var day = new Date(now);
            day.setDate(day.getDate() - i);
            data.push({
                push_time: day.toISOString(),
                count: Math.floor(Math.random() * 100) + 20
            });
        }
    }
    return data;
}

function updatePushTrendChart(data) {
    if (!pushTrendChart) return;
    
    var xAxisData = data.map(function(item) {
        var date = new Date(item.timestamp || item.push_time);
        if (currentTrendRange === '24h') {
            return date.getHours() + ':00';
        } else {
            return (date.getMonth() + 1) + '-' + date.getDate();
        }
    });
    
    var seriesData = data.map(function(item) { return item.count || 0; });
    
    // 响应式配置
    var isMobile = window.innerWidth < 768;
    var gridLeft = isMobile ? '2%' : '3%';
    var gridRight = isMobile ? '2%' : '4%';
    var axisLabelFontSize = isMobile ? 9 : 11;
    var tooltipFontSize = isMobile ? 11 : 13;
    
    // 检测是否为暗色主题
    var isDark = document.body.classList.contains('theme-dark') || !document.body.classList.contains('theme-light');
    var textColor = isDark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)';
    var gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
    var splitLineColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)';
    
    var option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: isDark ? 'rgba(30, 30, 40, 0.95)' : 'rgba(255, 255, 255, 0.95)',
            borderColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            padding: [10, 14],
            textStyle: { color: isDark ? '#fff' : '#333', fontSize: tooltipFontSize },
            formatter: function(params) {
                return '<div style="font-weight:600;margin-bottom:4px;">' + params[0].name + '</div>' +
                       '<div style="display:flex;align-items:center;gap:8px;">' +
                       '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2);"></span>' +
                       '<span>推送: <strong style="color:#667eea;">' + params[0].value + '</strong> 条</span></div>';
            },
            extraCssText: 'border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);'
        },
        grid: {
            left: gridLeft,
            right: gridRight,
            bottom: isMobile ? '2%' : '3%',
            top: isMobile ? '15px' : '20px',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: xAxisData,
            axisLine: { lineStyle: { color: gridColor } },
            axisTick: { show: false },
            axisLabel: { 
                color: textColor, 
                fontSize: axisLabelFontSize,
                margin: 8,
                rotate: isMobile ? 45 : 0
            }
        },
        yAxis: {
            type: 'value',
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } },
            axisLabel: { color: textColor, fontSize: axisLabelFontSize }
        },
        series: [{
            name: '推送量',
            type: 'line',
            smooth: 0.4,
            symbol: 'circle',
            symbolSize: isMobile ? 5 : 8,
            showSymbol: false,
            hoverAnimation: true,
            lineStyle: { width: isMobile ? 2 : 3, color: '#667eea' },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(102, 126, 234, 0.35)' },
                    { offset: 0.5, color: 'rgba(102, 126, 234, 0.15)' },
                    { offset: 1, color: 'rgba(102, 126, 234, 0.02)' }
                ])
            },
            itemStyle: { 
                color: '#667eea',
                borderWidth: 2,
                borderColor: '#fff',
                shadowColor: 'rgba(102, 126, 234, 0.5)',
                shadowBlur: 8
            },
            emphasis: {
                scale: true,
                scaleSize: 2
            },
            data: seriesData,
            animationDuration: 1500,
            animationEasing: 'cubicOut'
        }]
    };
    
    pushTrendChart.setOption(option, true);
}

function loadPushChannelData() {
    if (!pushChannelChart) return;
    
    pushChannelChart.showLoading({
        text: '加载中...',
        color: '#667eea',
        textColor: 'rgba(255,255,255,0.6)',
        maskColor: 'rgba(0,0,0,0.1)'
    });
    
    apiFetch('/api/history?limit=500')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            pushChannelChart.hideLoading();
            if (data.data && Array.isArray(data.data)) {
                updatePushChannelChart(data.data);
            } else {
                updatePushChannelChart(generateMockChannelData());
            }
        })
        .catch(function() {
            pushChannelChart.hideLoading();
            updatePushChannelChart(generateMockChannelData());
        });
}

function generateMockChannelData() {
    return [
        { channel: '企业微信', count: 245 },
        { channel: '飞书', count: 189 },
        { channel: '钉钉', count: 156 },
        { channel: 'Telegram', count: 98 },
        { channel: 'Email', count: 67 },
        { channel: '其他', count: 45 }
    ];
}

function updatePushChannelChart(data) {
    if (!pushChannelChart) return;
    
    var channelMap = {};
    data.forEach(function(item) {
        var channel = item.channel || item.name || '未知';
        channelMap[channel] = (channelMap[channel] || 0) + (item.count || item.value || 1);
    });
    
    var channelData = Object.keys(channelMap).map(function(name) {
        return { name: name, value: channelMap[name] };
    });
    
    if (channelData.length === 0) {
        channelData.push({ name: '暂无数据', value: 1 });
    }
    
    // 响应式配置
    var isMobile = window.innerWidth < 768;
    var tooltipFontSize = isMobile ? 11 : 13;
    
    // 检测是否为暗色主题
    var isDark = document.body.classList.contains('theme-dark') || !document.body.classList.contains('theme-light');
    var textColor = isDark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)';
    
    // 渐变色数组
    var colors = [
        { start: '#667eea', end: '#764ba2' },
        { start: '#f093fb', end: '#f5576c' },
        { start: '#4facfe', end: '#00f2fe' },
        { start: '#43e97b', end: '#38f9d7' },
        { start: '#fa709a', end: '#fee140' },
        { start: '#a8edea', end: '#fed6e3' },
        { start: '#d299c2', end: '#fef9d7' },
        { start: '#89f7fe', end: '#66a6ff' }
    ];
    
    var option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            backgroundColor: isDark ? 'rgba(30, 30, 40, 0.95)' : 'rgba(255, 255, 255, 0.95)',
            borderColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            padding: [10, 14],
            textStyle: { color: isDark ? '#fff' : '#333', fontSize: tooltipFontSize },
            formatter: function(params) {
                if (params.name === '暂无数据') return '<div style="text-align:center;color:#999;">暂无数据</div>';
                return '<div style="font-weight:600;margin-bottom:4px;">' + params.name + '</div>' +
                       '<div style="color:#888;">推送: <strong style="color:#667eea;">' + params.value + '</strong> 条</div>' +
                       '<div style="color:#888;">占比: <strong style="color:#f5576c;">' + params.percent.toFixed(1) + '%</strong></div>';
            },
            extraCssText: 'border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);'
        },
        legend: {
            orient: isMobile ? 'horizontal' : 'vertical',
            bottom: isMobile ? '5%' : 'auto',
            top: isMobile ? 'auto' : 'center',
            right: isMobile ? 'auto' : '3%',
            left: isMobile ? 'center' : 'auto',
            width: isMobile ? '90%' : 'auto',
            itemWidth: 12,
            itemHeight: 12,
            itemGap: isMobile ? 16 : 12,
            textStyle: { 
                color: textColor, 
                fontSize: isMobile ? 10 : 12,
                lineHeight: isMobile ? 20 : 20
            },
            pageTextStyle: { color: textColor },
            pageIconColor: '#667eea',
            pageIconInactiveColor: 'rgba(255,255,255,0.3)'
        },
        series: [{
            name: '推送渠道',
            type: 'pie',
            radius: isMobile ? ['40%', '65%'] : ['40%', '70%'],
            center: isMobile ? ['50%', '45%'] : ['38%', '50%'],
            roseType: false,
            avoidLabelOverlap: true,
            itemStyle: {
                borderRadius: 8,
                borderColor: isDark ? '#1a1a2e' : '#fff',
                borderWidth: 2
            },
            label: {
                show: false,
                position: 'outside',
                formatter: '{b}\n{d}%',
                color: textColor
            },
            labelLine: {
                show: false,
                length: 15,
                length2: 10,
                smooth: true
            },
            emphasis: {
                scale: true,
                scaleSize: 8,
                itemStyle: {
                    shadowBlur: 20,
                    shadowColor: 'rgba(102, 126, 234, 0.5)'
                }
            },
            data: channelData.map(function(item, index) {
                var color = colors[index % colors.length];
                return {
                    name: item.name,
                    value: item.value,
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                            { offset: 0, color: color.start },
                            { offset: 1, color: color.end }
                        ])
                    }
                };
            }),
            animationType: 'expansion',
            animationDuration: 1200,
            animationEasing: 'cubicOut'
        }]
    };
    
    pushChannelChart.setOption(option, true);
}

function setPushTrendRange(range) {
    currentTrendRange = range;
    
    // 更新按钮状态
    var buttons = document.querySelectorAll('.chart-tabs .btn');
    buttons.forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.range === range);
    });
    
    // 重新加载数据
    loadPushTrendData();
}

// ========== 导出到全局 ==========
window.initCharts = initCharts;
window.loadChartData = loadChartData;
window.setPushTrendRange = setPushTrendRange;


// ========== 统计面板功能 ==========
function updateStatsTabBtn(btn) {
    document.querySelectorAll("#panel-stats .btn-group .btn").forEach(function(b) {
        b.classList.remove("active");
    });
    if (btn) btn.classList.add("active");
}

async function refreshStatsCharts() {
    loadPushTrendChart(currentPushRange || "24h");
    loadChannelPieChart();
    loadEventTypeChart();
    loadStatsOverview();
}

async function loadStatsOverview() {
    var el = document.getElementById("stats-total-push");
    if (!el) return;
    try {
        var r = await fetch("/api/stats/chart-data");
        var data = await r.json();
        if (!data.success) return;
        
        // 使用API返回的概览数据
        if (data.overview) {
            document.getElementById("stats-total-push").textContent = data.overview.total || 0;
            document.getElementById("stats-today-push").textContent = data.overview.today || 0;
        }
        
        // 计算峰值时段和日均
        var trendData = data.trend7d || [];
        var total = data.overview ? data.overview.total : 0;
        var maxHour = 0, maxHourCount = 0;
        var dayCounts = {};
        trendData.forEach(function(item) {
            var d = new Date(item.timestamp);
            var hour = d.getHours();
            if (item.count > maxHourCount) {
                maxHourCount = item.count;
                maxHour = hour;
            }
            var dayKey = d.toDateString();
            dayCounts[dayKey] = (dayCounts[dayKey] || 0) + item.count;
        });
        var days = Object.keys(dayCounts).length;
        var avgDaily = days > 0 ? Math.round(total / days) : 0;
        
        document.getElementById("stats-peak-hour").textContent = maxHour + ":00";
        document.getElementById("stats-avg-daily").textContent = avgDaily;
    } catch (e) {
        console.error("loadStatsOverview error", e);
    }
}

async function loadEventTypeChart() {
    var el = document.getElementById("event-type-chart");
    if (!el) return;
    try {
        var r = await fetch("/api/events/list");
        var data = await r.json();
        if (data.status !== "success") {
            el.innerHTML = "<div class=\"text-center text-muted py-5\">加载失败</div>";
            return;
        }
        var events = data.events || [];
        if (events.length === 0) {
            el.innerHTML = "<div class=\"text-center text-muted py-5\"><i class='fas fa-chart-pie me-2'></i>暂无事件数据</div>";
            return;
        }
        
        // 响应式配置
        var isMobile = window.innerWidth < 768;
        var tooltipFontSize = isMobile ? 11 : 13;
        
        // 检测是否为暗色主题
        var isDark = document.body.classList.contains('theme-dark') || !document.body.classList.contains('theme-light');
        var textColor = isDark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)';
        
        var chartData = events.slice(0, 10).map(function(e) {
            return { 
                value: 1, 
                name: e.name || e.id, 
                itemStyle: { 
                    color: e.color || "#007bff",
                    borderColor: isDark ? '#1a1a2e' : '#fff',
                    borderWidth: 2
                }
            };
        });
        
        var chart = echarts.init(el);
        chart.setOption({
            backgroundColor: 'transparent',
            tooltip: {
                trigger: "item",
                backgroundColor: isDark ? 'rgba(30, 30, 40, 0.95)' : 'rgba(255, 255, 255, 0.95)',
                borderColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
                borderWidth: 1,
                padding: [10, 14],
                textStyle: { color: isDark ? '#fff' : '#333', fontSize: tooltipFontSize },
                formatter: function(params) {
                    return '<div style="font-weight:600;margin-bottom:4px;">' + params.name + '</div>' +
                           '<div style="color:#888;">事件类型</div>';
                },
                extraCssText: 'border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);'
            },
            legend: {
                orient: isMobile ? 'horizontal' : 'vertical',
                bottom: isMobile ? '0%' : 'auto',
                top: isMobile ? 'auto' : 'center',
                right: isMobile ? 'auto' : '3%',
                left: isMobile ? 'center' : 'auto',
                width: isMobile ? '95%' : 'auto',
                itemWidth: 10,
                itemHeight: 10,
                itemGap: isMobile ? 12 : 10,
                textStyle: { 
                    color: textColor, 
                    fontSize: isMobile ? 9 : 11
                }
            },
            series: [{
                type: "pie",
                radius: isMobile ? ["35%", "60%"] : ["40%", "70%"],
                center: ['50%', isMobile ? '50%' : '50%'],
                avoidLabelOverlap: true,
                itemStyle: { 
                    borderRadius: 8, 
                    borderColor: isDark ? '#1a1a2e' : '#fff', 
                    borderWidth: 2 
                },
                label: { 
                    show: false 
                },
                emphasis: {
                    scale: true,
                    scaleSize: 6,
                    itemStyle: {
                        shadowBlur: 15,
                        shadowColor: 'rgba(0, 0, 0, 0.3)'
                    }
                },
                data: chartData,
                animationDuration: 1200,
                animationEasing: 'cubicOut'
            }]
        });
        
        // 响应窗口变化
        window.addEventListener('resize', function() {
            chart.resize();
        });
    } catch (e) {
        el.innerHTML = "<div class=\"text-center text-muted py-5\"><i class='fas fa-exclamation-triangle me-2'></i>加载失败</div>";
    }
}

window.refreshStatsCharts = refreshStatsCharts;
window.loadStatsOverview = loadStatsOverview;
window.loadEventTypeChart = loadEventTypeChart;


// ========== 统计面板初始化 ==========
function initStatsPanel() {
    // 初始化图表
    initCharts();
    
    // 确保图表容器可见后再加载数据
    setTimeout(function() {
        // 调整图表大小
        if (pushTrendChart) pushTrendChart.resize();
        if (pushChannelChart) pushChannelChart.resize();
        
        // 加载图表数据
        loadChartData();
        // 加载统计概览
        loadStatsOverview();
        // 加载事件类型图表
        loadEventTypeChart();
    }, 100);
}

// ========== 兼容性别名 ==========
window.setPushTrendRange = function(range) {
    currentTrendRange = range;
    loadPushTrendData();
};

window.initStatsPanel = initStatsPanel;
