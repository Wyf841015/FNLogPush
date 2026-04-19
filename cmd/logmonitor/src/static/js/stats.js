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
    if (!pushTrendChart) return;
    
    pushTrendChart.showLoading({
        text: '加载中...',
        color: '#667eea',
        textColor: 'rgba(255,255,255,0.6)',
        maskColor: 'rgba(0,0,0,0.1)'
    });
    
    // 使用新的统计API
    apiFetch('/api/stats/chart-data')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            pushTrendChart.hideLoading();
            if (data.success) {
                var trendData = currentTrendRange === '24h' ? data.trend24h : data.trend7d;
                if (trendData && trendData.length > 0) {
                    updatePushTrendChart(trendData);
                } else {
                    updatePushTrendChart(generateMockTrendData());
                }
                // 更新概览统计
                if (data.overview) {
                    updateStatsOverview(data.overview);
                }
                // 更新渠道数据
                if (data.channels && data.channels.length > 0 && data.channels[0].value > 0) {
                    updatePushChannelChart(data.channels);
                }
            } else {
                updatePushTrendChart(generateMockTrendData());
            }
        })
        .catch(function() {
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
    
    var option = {
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(30, 30, 40, 0.9)',
            borderColor: 'rgba(255,255,255,0.2)',
            textStyle: { color: '#fff' },
            formatter: function(params) {
                return params[0].name + '<br/>推送: ' + params[0].value + ' 条';
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            top: '10px',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: xAxisData,
            axisLine: { lineStyle: { color: 'rgba(255,255,255,0.3)' } },
            axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
        },
        yAxis: {
            type: 'value',
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
            axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
        },
        series: [{
            name: '推送量',
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { width: 2, color: '#667eea' },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(102, 126, 234, 0.4)' },
                    { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
                ])
            },
            itemStyle: { color: '#667eea' },
            data: seriesData
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
        var channel = item.channel || '未知';
        channelMap[channel] = (channelMap[channel] || 0) + (item.count || 1);
    });
    
    var channelData = Object.keys(channelMap).map(function(name) {
        return { name: name, value: channelMap[name] };
    });
    
    if (channelData.length === 0) {
        channelData.push({ name: '暂无数据', value: 1 });
    }
    
    var colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'];
    
    var option = {
        tooltip: {
            trigger: 'item',
            backgroundColor: 'rgba(30, 30, 40, 0.9)',
            borderColor: 'rgba(255,255,255,0.2)',
            textStyle: { color: '#fff' },
            formatter: '{b}: {c} 条 ({d}%)'
        },
        legend: {
            orient: 'vertical',
            right: '5%',
            top: 'center',
            textStyle: { color: 'rgba(255,255,255,0.7)', fontSize: 11 }
        },
        series: [{
            name: '推送渠道',
            type: 'pie',
            radius: ['45%', '70%'],
            center: ['35%', '50%'],
            avoidLabelOverlap: false,
            label: { show: false },
            emphasis: {
                label: { show: true, fontSize: 12, fontWeight: 'bold' }
            },
            labelLine: { show: false },
            data: channelData.map(function(item, index) {
                return {
                    name: item.name,
                    value: item.value,
                    itemStyle: { color: colors[index % colors.length] }
                };
            })
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
        var r = await fetch("/api/push/history?limit=1000");
        var data = await r.json();
        if (data.status !== "success") return;
        var records = data.records || [];
        var total = records.length;
        var today = new Date().toDateString();
        var todayCount = records.filter(function(rec) {
            return new Date(rec.timestamp).toDateString() === today;
        }).length;
        var hourCounts = {};
        records.forEach(function(rec) {
            var h = new Date(rec.timestamp).getHours();
            hourCounts[h] = (hourCounts[h] || 0) + 1;
        });
        var peakHour = 0, peakCount = 0;
        Object.keys(hourCounts).forEach(function(h) {
            if (hourCounts[h] > peakCount) {
                peakCount = hourCounts[h];
                peakHour = parseInt(h);
            }
        });
        var days = new Set();
        records.forEach(function(rec) {
            days.add(new Date(rec.timestamp).toDateString());
        });
        var avgDaily = days.size > 0 ? Math.round(total / days.size) : 0;
        document.getElementById("stats-total-push").textContent = total;
        document.getElementById("stats-today-push").textContent = todayCount;
        document.getElementById("stats-peak-hour").textContent = peakHour + ":00";
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
            el.innerHTML = "<div class=\"text-center text-muted py-5\">暂无数据</div>";
            return;
        }
        var chartData = events.slice(0, 10).map(function(e) {
            return { value: 1, name: e.name || e.id, itemStyle: { color: e.color || "#007bff" } };
        });
        var chart = echarts.init(el);
        chart.setOption({
            tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
            series: [{
                type: "pie",
                radius: ["40%", "70%"],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 6, borderColor: "#1a1a2e", borderWidth: 2 },
                label: { show: true, formatter: "{b}
{d}%", fontSize: 10 },
                data: chartData
            }]
        });
    } catch (e) {
        el.innerHTML = "<div class=\"text-center text-muted py-5\">加载失败: " + e.message + "</div>";
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
