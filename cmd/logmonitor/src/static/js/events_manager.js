// 事件管理
var FONT_AWESOME_ICONS = ["fa-bell","fa-exclamation-circle","fa-exclamation-triangle","fa-info-circle","fa-check-circle","fa-times-circle","fa-question-circle","fa-cog","fa-cogs","fa-wrench","fa-tools","fa-server","fa-desktop","fa-microchip","fa-hdd","fa-database","fa-cpu","fa-fan","fa-bolt","fa-plug","fa-power-off","fa-sync","fa-refresh","fa-wifi","fa-ethernet","fa-globe","fa-cloud","fa-upload","fa-download","fa-share","fa-folder","fa-file","fa-save","fa-trash","fa-edit","fa-user","fa-users","fa-key","fa-lock","fa-lock-open","fa-shield","fa-eye","fa-search","fa-filter","fa-chart-bar","fa-clock","fa-calendar","fa-alarm","fa-bug","fa-code","fa-terminal","fa-rocket","fa-signal","fa-envelope","fa-paper-plane","fa-comment","fa-phone","fa-camera","fa-video","fa-music","fa-gamepad","fa-print","fa-home","fa-hospital","fa-bank","fa-store","fa-tag","fa-money-bill","fa-heart","fa-medkit","fa-car","fa-bus","fa-train","fa-plane","fa-sun","fa-moon","fa-star","fa-fire","fa-leaf","fa-coffee","fa-book","fa-graduation-cap"];
var eventsData = [];
var filteredEvents = [];
var selectedEvents = new Set();

function esc(s) {
    if (s == null || s == undefined) return "";
    if (typeof s !== "string") s = String(s);
    return s.replace(/[&<>"']/g, function(m) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
    });
}

// 刷新事件列表
async function refreshEventsList() {
    var c = document.getElementById("events-list-container");
    if (!c) return;
    c.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin"></i></div>';
    try {
        var r = await fetch("/api/events/list");
        var rs = await r.json();
        if (rs.status === "success") {
            eventsData = rs.events || [];
            selectedEvents.clear();
            filterEvents();
            updateCategoryFilter(eventsData);
            updateEventsStats(eventsData.length, 0);
        } else {
            c.innerHTML = '<div class="alert alert-danger">' + esc(rs.error) + '</div>';
        }
    } catch (e) {
        c.innerHTML = '<div class="alert alert-danger">' + esc(e.message) + '</div>';
    }
}

// 渲染事件列表
function renderEventsList(evts) {
    var c = document.getElementById("events-list-container");
    if (!c) return;
    filteredEvents = evts;
    
    if (evts.length === 0) {
        c.innerHTML = '<div class="text-center text-muted py-4"><i class="fas fa-inbox fa-2x"></i><p class="mt-2">暂无事件</p></div>';
        return;
    }
    
    var h = '<div class="table-responsive"><table class="table table-hover table-sm table-borderless">';
    h += '<thead><tr>';
    h += '<th style="width:30px;"><input type="checkbox" class="form-check-input" id="select-all-events" onchange="toggleSelectAllEvents(this.checked)"></th>';
    h += '<th style="width:40px;"></th><th>事件ID</th><th>名称</th>';
    h += '<th class="d-none d-md-table-cell">分类</th>';
    h += '<th class="d-none d-lg-table-cell" style="width:80px;">颜色</th>';
    h += '<th style="width:100px;">操作</th>';
    h += '</tr></thead><tbody>';
    
    evts.forEach(function(e) {
        var s = e.color ? "color:" + e.color : "";
        var checked = selectedEvents.has(e.id) ? "checked" : "";
        h += '<tr class="event-row" data-event-id="' + esc(e.id) + '">';
        h += '<td><input type="checkbox" class="form-check-input event-checkbox" value="' + esc(e.id) + '" ' + checked + ' onchange="toggleEventSelection(\'' + esc(e.id) + '\')"></td>';
        h += '<td><i class="fas ' + (e.icon || "fa-bell") + '" style="' + s + '"></i></td>';
        h += '<td><code class="small">' + esc(e.id) + '</code></td>';
        h += '<td class="small">' + esc(e.name) + '</td>';
        h += '<td class="d-none d-md-table-cell"><span class="badge bg-secondary small">' + esc(e.category || "默认") + '</span></td>';
        h += '<td class="d-none d-lg-table-cell"><span class="badge" style="background:' + (e.color || "#007bff") + ';color:#fff;padding:2px 6px;font-size:10px;">' + esc(e.color || "#007bff") + '</span></td>';
        h += '<td>';
        h += '<button class="btn btn-sm btn-outline-primary py-0 px-1" onclick="editEvent(\'' + esc(e.id) + '\')" title="编辑"><i class="fas fa-edit"></i></button> ';
        h += '<button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="confirmDeleteEvent(\'' + esc(e.id) + '\')" title="删除"><i class="fas fa-trash"></i></button>';
        h += '</td></tr>';
    });
    
    c.innerHTML = h + '</tbody></table></div>';
    updateSelectAllState();
}

// 更新分类筛选器
function updateCategoryFilter(evts) {
    var sel = document.getElementById("event-category-filter");
    if (!sel) return;
    
    var cats = {};
    evts.forEach(function(e) {
        cats[e.category || "默认"] = 1;
    });
    
    var cur = sel.value;
    sel.innerHTML = '<option value="">全部分类</option>';
    Object.keys(cats).sort().forEach(function(c) {
        sel.innerHTML += '<option value="' + c + '">' + c + '</option>';
    });
    sel.value = cur;
}

// 过滤事件
function filterEvents() {
    var txt = (document.getElementById("event-search") || {}).value || "";
    var cat = (document.getElementById("event-category-filter") || {}).value || "";
    txt = txt.toLowerCase();
    
    var f = eventsData.filter(function(e) {
        return (!txt || (e.id && e.id.toLowerCase().indexOf(txt) !== -1) || (e.name && e.name.toLowerCase().indexOf(txt) !== -1)) 
               && (!cat || (e.category || "默认") === cat);
    });
    
    renderEventsList(f);
    
    var clearBtn = document.getElementById("clear-search-btn");
    if (clearBtn) {
        clearBtn.style.display = txt ? "block" : "none";
    }
    
    var isFiltered = txt || cat;
    updateEventsStats(eventsData.length, f.length, isFiltered, txt, cat);
}

// 更新事件统计
function updateEventsStats(total, filtered, isFiltered, searchText, category) {
    var totalEl = document.getElementById("events-total-count");
    var filterInfo = document.getElementById("events-filter-info");
    
    if (totalEl) totalEl.textContent = total;
    
    if (filterInfo) {
        if (isFiltered && filtered !== total) {
            filterInfo.style.display = "inline";
            filterInfo.innerHTML = '<span class="text-primary">筛选: <strong>' + filtered + '</strong> 条</span> ' +
                '<button class="btn btn-sm btn-link p-0 ms-1" onclick="clearEventSearch()">清除筛选</button>';
        } else {
            filterInfo.style.display = "none";
        }
    }
}

// 清空搜索
function clearEventSearch() {
    var searchInput = document.getElementById("event-search");
    var categorySelect = document.getElementById("event-category-filter");
    
    if (searchInput) searchInput.value = "";
    if (categorySelect) categorySelect.value = "";
    
    filterEvents();
}

// ============ 批量选择功能 ============

// 切换单个事件选择状态
function toggleEventSelection(eventId) {
    if (selectedEvents.has(eventId)) {
        selectedEvents.delete(eventId);
    } else {
        selectedEvents.add(eventId);
    }
    updateSelectAllState();
}

// 全选/取消所有可见事件
function toggleSelectAllEvents(checked) {
    var checkboxes = document.querySelectorAll(".event-checkbox");
    checkboxes.forEach(function(cb) {
        cb.checked = checked;
        var id = cb.value;
        if (checked) {
            selectedEvents.add(id);
        } else {
            selectedEvents.delete(id);
        }
    });
    updateSelectAllState();
}

// 选中所有可见事件
function selectAllVisibleEvents() {
    filteredEvents.forEach(function(e) {
        selectedEvents.add(e.id);
    });
    var checkboxes = document.querySelectorAll(".event-checkbox");
    checkboxes.forEach(function(cb) {
        cb.checked = true;
    });
    updateSelectAllState();
    showNotification("已选中 " + selectedEvents.size + " 个事件", "info");
}

// 取消所有选中
function deselectAllVisibleEvents() {
    selectedEvents.clear();
    var checkboxes = document.querySelectorAll(".event-checkbox");
    checkboxes.forEach(function(cb) {
        cb.checked = false;
    });
    updateSelectAllState();
    showNotification("已取消所有选择", "info");
}

// 更新全选框状态
function updateSelectAllState() {
    var selectAll = document.getElementById("select-all-events");
    var checkboxes = document.querySelectorAll(".event-checkbox");
    
    if (!selectAll || checkboxes.length === 0) return;
    
    var checkedCount = 0;
    checkboxes.forEach(function(cb) {
        if (cb.checked) checkedCount++;
    });
    
    if (checkedCount === 0) {
        selectAll.checked = false;
        selectAll.indeterminate = false;
    } else if (checkedCount === checkboxes.length) {
        selectAll.checked = true;
        selectAll.indeterminate = false;
    } else {
        selectAll.checked = false;
        selectAll.indeterminate = true;
    }
}

// 确认删除事件
function confirmDeleteEvent(eventId) {
    if (confirm("确定要删除事件 '" + eventId + "' 吗？")) {
        deleteEvent(eventId);
    }
}

// 删除事件
async function deleteEvent(eventId) {
    try {
        var resp = await fetch("/api/events/delete", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: eventId})
        });
        var result = await resp.json();
        
        if (result.success) {
            showNotification("事件已删除", "success");
            refreshEventsList();
        } else {
            showNotification(result.error || "删除失败", "danger");
        }
    } catch (e) {
        showNotification("删除失败: " + e.message, "danger");
    }
}

// 编辑事件
function editEvent(eventId) {
    // 查找事件数据
    var event = eventsData.find(function(e) { return e.id === eventId; });
    if (!event) {
        showNotification("未找到事件: " + eventId, "danger");
        return;
    }
    
    // 填充编辑表单
    var modal = new bootstrap.Modal(document.getElementById("addEventModal"));
    document.getElementById("event-id-input").value = event.id;
    document.getElementById("event-id-input").readOnly = true;
    document.getElementById("event-name-input").value = event.name || "";
    document.getElementById("event-icon-input").value = event.icon || "fa-bell";
    document.getElementById("event-color-input").value = event.color || "#007bff";
    
    // 显示模态框
    modal.show();
}

// 显示添加事件模态框
function showAddEventModal() {
    document.getElementById("event-id-input").value = "";
    document.getElementById("event-id-input").readOnly = false;
    document.getElementById("event-name-input").value = "";
    document.getElementById("event-icon-input").value = "fa-bell";
    document.getElementById("event-color-input").value = "#007bff";
    
    var modal = new bootstrap.Modal(document.getElementById("addEventModal"));
    modal.show();
}

// 保存事件
async function saveEvent() {
    var id = document.getElementById("event-id-input").value.trim();
    var name = document.getElementById("event-name-input").value.trim();
    var icon = document.getElementById("event-icon-input").value;
    var color = document.getElementById("event-color-input").value;
    
    if (!id || !name) {
        showNotification("事件ID和名称不能为空", "warning");
        return;
    }
    
    var isEdit = document.getElementById("event-id-input").readOnly;
    var url = isEdit ? "/api/events/update" : "/api/events/add";
    
    try {
        var resp = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: id, name: name, icon: icon, color: color})
        });
        var result = await resp.json();
        
        if (result.success) {
            showNotification(isEdit ? "事件已更新" : "事件已添加", "success");
            bootstrap.Modal.getInstance(document.getElementById("addEventModal")).hide();
            refreshEventsList();
        } else {
            showNotification(result.error || "保存失败", "danger");
        }
    } catch (e) {
        showNotification("保存失败: " + e.message, "danger");
    }
}

// 键盘快捷键支持
document.addEventListener("DOMContentLoaded", function() {
    var searchInput = document.getElementById("event-search");
    if (searchInput) {
        searchInput.addEventListener("keydown", function(e) {
            // Escape 清空搜索
            if (e.key === "Escape") {
                clearEventSearch();
                this.blur();
            }
        });
    }
});



// ========== 事件颜色选择 ==========
function selectEventColor(color) {
    var colorInput = document.getElementById('event-color');
    var colorPresets = document.querySelectorAll('.color-preset');
    if (colorInput) { colorInput.value = color; }
    colorPresets.forEach(function(btn) {
        if (btn.getAttribute('style').indexOf(color) !== -1) {
            btn.style.border = '2px solid #fff';
            btn.style.boxShadow = '0 0 0 2px ' + color;
        } else {
            btn.style.border = '2px solid transparent';
            btn.style.boxShadow = 'none';
        }
    });
}

function showIconPicker() {
    var preview = document.getElementById('event-icon-preview');
    var iconInput = document.getElementById('event-icon');
    var modal = new bootstrap.Modal(document.getElementById('iconPickerModal'));
    modal.show();
    renderIconPickerGrid(function(icon) {
        if (iconInput) iconInput.value = icon;
        if (preview) preview.innerHTML = '<i class="fas ' + icon + '"></i>';
        bootstrap.Modal.getInstance(document.getElementById('iconPickerModal')).hide();
    });
}

function renderIconPickerGrid(onSelect) {
    var grid = document.getElementById('icon-picker-grid');
    if (!grid) return;
    var currentIcon = (document.getElementById('event-icon') || {}).value || 'fa-bell';
    var html = '';
    FONT_AWESOME_ICONS.forEach(function(icon) {
        var sel = icon === currentIcon ? 'selected border-primary' : '';
        html += '<div class="col-2 text-center py-2">';
        html += '<button type="button" class="btn icon-btn ' + sel + '" data-icon="' + icon + '" onclick="pickIcon(\'' + icon + '\')">';
        html += '<i class="fas ' + icon + '"></i></button></div>';
    });
    grid.innerHTML = html;
    window._iconPickerCallback = onSelect;
}

function pickIcon(icon) {
    document.querySelectorAll('.icon-btn').forEach(function(btn) {
        btn.classList.remove('selected', 'border-primary');
        if (btn.getAttribute('data-icon') === icon) btn.classList.add('selected', 'border-primary');
    });
    if (typeof window._iconPickerCallback === 'function') window._iconPickerCallback(icon);
}

window.selectEventColor = selectEventColor;
window.showIconPicker = showIconPicker;
window.pickIcon = pickIcon;
