// ========== sidebar.js - 侧边栏导航模块 ==========

// ========== 状态变量 ==========
let sidebarOpen = false;
let sidebarCollapsed = false;

// ========== 侧边栏切换 ==========

/**
 * 切换侧边栏（移动端）
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebarContainer');
    const overlay = document.getElementById('sidebarOverlay');
    const toggle = document.getElementById('mobileMenuToggle');
    
    if (!sidebar) return;
    
    sidebarOpen = !sidebarOpen;
    
    if (sidebarOpen) {
        sidebar.classList.add('mobile-open');
        overlay?.classList.add('active');
        if (toggle) toggle.innerHTML = '<i class="fas fa-times"></i>';
        document.body.style.overflow = 'hidden';
    } else {
        sidebar.classList.remove('mobile-open');
        overlay?.classList.remove('active');
        if (toggle) toggle.innerHTML = '<i class="fas fa-bars"></i>';
        document.body.style.overflow = '';
    }
}

/**
 * 关闭侧边栏（移动端）
 */
function closeSidebar() {
    if (sidebarOpen) {
        toggleSidebar();
    }
}

/**
 * 切换侧边栏收缩/展开（桌面端）
 */
function toggleSidebarCollapse() {
    const sidebar = document.getElementById('sidebarContainer');
    const mainWrapper = document.getElementById('mainWrapper');
    
    if (!sidebar) return;
    
    sidebarCollapsed = !sidebarCollapsed;
    
    if (sidebarCollapsed) {
        sidebar.classList.add('collapsed');
        mainWrapper?.classList.add('sidebar-collapsed');
    } else {
        sidebar.classList.remove('collapsed');
        mainWrapper?.classList.remove('sidebar-collapsed');
    }
    
    // 保存状态到本地存储
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
}

/**
 * 切换导航面板
 * @param {HTMLElement} element - 触发元素
 * @param {string} target - 目标面板ID
 */
function switchNavPanel(element, target) {
    if (!element || !target) return;
    
    // 移除所有面板的active状态
    document.querySelectorAll('.nav-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // 激活目标面板
    const targetPanel = document.getElementById(target);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }
    
    // 更新导航active状态
    syncNavActive(target);
    
    // 移动端关闭侧边栏
    closeSidebar();
}

/**
 * 同步导航active状态
 * @param {string} target - 目标面板ID
 */
function syncNavActive(target) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const activeItem = document.querySelector(`.nav-item[onclick*="'${target}'"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }
}

/**
 * 初始化侧边栏状态
 */
function initSidebar() {
    // 从本地存储恢复收缩状态
    const savedCollapsed = localStorage.getItem('sidebarCollapsed');
    if (savedCollapsed === 'true') {
        sidebarCollapsed = true;
        const sidebar = document.getElementById('sidebarContainer');
        const mainWrapper = document.getElementById('mainWrapper');
        if (sidebar) sidebar.classList.add('collapsed');
        if (mainWrapper) mainWrapper.classList.add('sidebar-collapsed');
    }
    
    // 绑定遮罩层点击关闭
    const overlay = document.getElementById('sidebarOverlay');
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }
    
    // 绑定 ESC 键关闭侧边栏
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebarOpen) {
            closeSidebar();
        }
    });
}

// 导出到全局
window.toggleSidebar = toggleSidebar;
window.closeSidebar = closeSidebar;
window.toggleSidebarCollapse = toggleSidebarCollapse;
window.switchNavPanel = switchNavPanel;
window.syncNavActive = syncNavActive;
window.initSidebar = initSidebar;
