// ========== history.js - 历史记录模块 ==========

// ========== 全局状态 ==========
let lastHistoryIndex = null;
let _historySearchTimer = null;
let historyKeyword = '';
let historyCurrentPage = 1;
const historyPageSize = 20;
let historyTotal = 0;

// ========== 日期筛选 ==========
let historyDateFilter = {
    startDate: '',
    endDate: ''
};

// ========== 历史搜索 ==========

function onHistorySearch(kw) {
    historyKeyword = kw.trim();
    clearTimeout(_historySearchTimer);
    _historySearchTimer = setTimeout(() => loadHistory(), 300);
}

function highlightKeyword(text, kw) {
    if (!kw || kw.trim() === '') return text;
    const escaped = kw.replace(/[.*+?^${}()|[\]\]/g, '\$&');
    const re = new RegExp(`(${escaped})`, 'gi');
    return text.replace(re, '<mark class="kw-highlight">$1</mark>');
}

// ========== 历史加载 ==========

function loadHistory(retry = 0) {
    const tbody = document.getElementById('history-table');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="7" class="text-center"><div class="spinner-border spinner-border-sm"></div> 加载中...</td></tr>';

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    const offset = (historyCurrentPage - 1) * historyPageSize;
    let queryParams = `limit=${historyPageSize}&offset=${offset}`;
    
    if (historyDateFilter.startDate) queryParams += `&start_date=${historyDateFilter.startDate}`;
    if (historyDateFilter.endDate) queryParams += `&end_date=${historyDateFilter.endDate}`;

    apiFetch(`/api/history?${queryParams}`, { signal: controller.signal })
        .then(response => response.json())
        .then(data => {
            clearTimeout(timeout);
            if (data.error && data.error.includes('监控程序未启动')) {
                if (retry < 1) setTimeout(() => loadHistory(1), 1500);
                else tbody.innerHTML = '<tr><td colspan="7" class="text-center"><i class="fas fa-power-off"></i> 监控程序未启动</td></tr>';
                return;
            }
            
            const records = data.records || [];
            historyTotal = data.total || 0;
            
            if (records.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center"><i class="fas fa-inbox"></i> 暂无推送记录</td></tr>';
                updatePaginationControls(0);
                return;
            }
            
            tbody.innerHTML = records.map(record => {
                const time = new Date(record.timestamp * 1000).toLocaleString('zh-CN', { hour12: false });
                const preview = record.preview ? escapeHtml(record.preview.substring(0, 80)) : '-';
                return `<tr onclick="showHistoryDetail(${record.id})" style="cursor:pointer;">
                    <td>${record.id}</td>
                    <td><small>${time}</small></td>
                    <td><span class="badge ${record.success ? 'bg-success' : 'bg-danger'}">${record.success ? '成功' : '失败'}</span></td>
                    <td><span class="badge bg-secondary">${record.count}条</span></td>
                    <td><small>${highlightKeyword(preview, historyKeyword)}...</small></td>
                    <td>${record.channel_results ? Object.entries(record.channel_results).map(([ch, r]) => `<span class="badge ${r ? 'bg-success' : 'bg-secondary'}">${ch}</span>`).join('') : '-'}</td>
                    <td><button class="btn btn-sm btn-outline-primary"><i class="fas fa-eye"></i></button></td>
                </tr>`;
            }).join('');
            
            updatePaginationControls(historyTotal);
        })
        .catch(error => {
            clearTimeout(timeout);
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger"><i class="fas fa-exclamation-triangle"></i> 加载失败</td></tr>`;
        });
}

// ========== 分页控制 ==========

function updatePaginationControls(total) {
    const prevBtn = document.getElementById('btn-prev-page');
    const nextBtn = document.getElementById('btn-next-page');
    const pageInfo = document.getElementById('history-page-info');
    const totalInfo = document.getElementById('history-total-info');
    if (!prevBtn || !nextBtn || !pageInfo || !totalInfo) return;
    const totalPages = Math.ceil(total / historyPageSize) || 1;
    if (historyCurrentPage > totalPages && totalPages > 0) historyCurrentPage = totalPages;
    pageInfo.textContent = `${historyCurrentPage}`;
    totalInfo.textContent = `${total}`;
    prevBtn.disabled = historyCurrentPage <= 1;
    nextBtn.disabled = historyCurrentPage >= totalPages;
}

function prevPage() { if (historyCurrentPage > 1) { historyCurrentPage--; loadHistory(); } }
function nextPage() { if (historyCurrentPage < Math.ceil(historyTotal / historyPageSize)) { historyCurrentPage++; loadHistory(); } }

// ========== 历史详情 ==========

function showHistoryDetail(historyId) {
    const modal = new bootstrap.Modal(document.getElementById('historyDetailModal'));
    const contentDiv = document.getElementById('historyDetailContent');
    if (!contentDiv) return;
    contentDiv.innerHTML = '<div class="text-center"><div class="spinner-border"></div></div>';
    modal.show();

    apiFetch(`/api/history/${historyId}`)
        .then(response => response.json())
        .then(result => {
            if (result.success && result.data) {
                const data = result.data;
                const time = new Date(data.timestamp).toLocaleString('zh-CN', { hour12: false });
                const successBadge = data.success ? '<span class="badge bg-success"><i class="fas fa-check"></i> 成功</span>' : '<span class="badge bg-danger"><i class="fas fa-times"></i> 失败</span>';
                contentDiv.innerHTML = `<div class="row">
                    <div class="col-md-6">
                        <table class="table table-sm">
                            <tr><th>ID</th><td>${data.id}</td></tr>
                            <tr><th>时间</th><td>${time}</td></tr>
                            <tr><th>状态</th><td>${successBadge}</td></tr>
                            <tr><th>数量</th><td>${data.count} 条</td></tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        ${data.channel_results ? `<h6>推送渠道</h6>` + Object.entries(data.channel_results).map(([ch, r]) => `<span class="badge ${r ? 'bg-success' : 'bg-secondary'} me-1">${ch}: ${r ? '成功' : '失败'}</span>`).join('') : ''}
                    </div>
                </div>
                <div class="mt-3"><h6>内容预览</h6><pre class="bg-dark text-light p-3 rounded" style="max-height:300px;overflow:auto;">${escapeHtml(data.content || '-')}</pre></div>`;
            } else {
                contentDiv.innerHTML = '<div class="alert alert-danger">加载失败</div>';
            }
        });
}

// ========== 刷新 & 筛选 ==========

function refreshHistory() { loadHistory(); }

function checkDatabaseFull() {
    const checkbox = document.getElementById('checkDatabaseFull');
    if (!checkbox) return;
    const checked = checkbox.checked;
    if (checked) {
        const msg = '⚠️ 检测到数据库已满！建议：\n1. 清理历史记录\n2. 减小保留天数\n3. 检查数据库文件大小';
        NotificationManager.warning('数据库告警', msg.replace(/\n/g, '<br>'));
    }
}

function checkDatabase() { loadHealthStatus(); }

// ========== 日期筛选 ==========

function onHistoryDateFilter() {
    const startDateInput = document.getElementById('history-date-start');
    const endDateInput = document.getElementById('history-date-end');
    historyDateFilter.startDate = startDateInput?.value || '';
    historyDateFilter.endDate = endDateInput?.value || '';
    historyCurrentPage = 1;
    loadHistory();
}

function clearHistoryDateFilter() {
    const startDateInput = document.getElementById('history-date-start');
    const endDateInput = document.getElementById('history-date-end');
    if (startDateInput) startDateInput.value = '';
    if (endDateInput) endDateInput.value = '';
    historyDateFilter.startDate = '';
    historyDateFilter.endDate = '';
    historyCurrentPage = 1;
    loadHistory();
}

function initHistoryDateFilter() {
    const startDateInput = document.getElementById('history-date-start');
    const endDateInput = document.getElementById('history-date-end');

    if (startDateInput && endDateInput) {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };

        startDateInput.value = formatDate(yesterday);
        endDateInput.value = formatDate(today);
        onHistoryDateFilter();
    }
}

// ========== 导出 ==========
window.loadHistory = loadHistory;
window.onHistorySearch = onHistorySearch;
window.refreshHistory = refreshHistory;
window.showHistoryDetail = showHistoryDetail;
window.updatePaginationControls = updatePaginationControls;
window.prevPage = prevPage;
window.nextPage = nextPage;
window.checkDatabaseFull = checkDatabaseFull;
window.checkDatabase = checkDatabase;
window.onHistoryDateFilter = onHistoryDateFilter;
window.clearHistoryDateFilter = clearHistoryDateFilter;
window.initHistoryDateFilter = initHistoryDateFilter;