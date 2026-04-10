// ========== fab.js - 浮动按钮和菜单模块 ==========

// ========== FAB菜单控制 ==========

function toggleFabMenu() {
    const fabMenu = document.getElementById('fabMenu');
    const mainBtnIcon = fabMenu.querySelector('.fab-main i');
    if (!fabMenu) return;
    
    fabMenu.classList.toggle('active');
    const isActive = fabMenu.classList.contains('active');
    
    if (mainBtnIcon) {
        mainBtnIcon.className = isActive ? 'fas fa-times' : 'fas fa-bars';
    }
    if (fabMenu.querySelector('.fab-main')) {
        fabMenu.querySelector('.fab-main').setAttribute('title', isActive ? '收起菜单' : '展开菜单');
    }
}

function showUserMenu() {
    const menu = document.getElementById('userMenuPopup');
    if (menu) menu.classList.toggle('active');
}

function hideUserMenu() {
    const menu = document.getElementById('userMenuPopup');
    if (menu) menu.classList.remove('active');
}

function toggleExpandableMenu() {
    const menu = document.getElementById('expandableMenu');
    if (menu) menu.classList.toggle('active');
}

function switchFabPanel(element, target) {
    if (!element || !target) return;
    
    // 移除所有面板的 active
    document.querySelectorAll('.fab-panel').forEach(p => p.classList.remove('active'));
    
    // 激活目标面板
    const panel = document.getElementById(target);
    if (panel) panel.classList.add('active');
    
    // 关闭FAB菜单
    if (target === 'userPanel') toggleFabMenu();
}

function switchConfigPanel(element, target) {
    if (!element || !target) return;
    
    // 移除所有面板的 active
    document.querySelectorAll('.config-panel').forEach(p => p.classList.remove('active'));
    
    // 激活目标面板
    const panel = document.getElementById(target);
    if (panel) panel.classList.add('active');
    
    // 更新侧边栏导航
    const nav = document.querySelector(`.nav-item[onclick*="'${target}'"]`);
    if (nav) {
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        nav.classList.add('active');
    }
}

// ========== 通用UI函数 ==========

function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    if (input.type === 'password') {
        input.type = 'text';
        if (button) button.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        if (button) button.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

function showConfirmModal(message, onConfirm) {
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const content = document.getElementById('confirmModalContent');
    if (content) content.textContent = message;
    
    const confirmBtn = document.getElementById('confirmModalBtn');
    if (confirmBtn) {
        confirmBtn.onclick = () => {
            modal.hide();
            if (onConfirm) onConfirm();
        };
    }
    modal.show();
}

function resetMonitor() {
    showConfirmModal('确定要重置监控状态吗？', () => {
        location.reload();
    });
}

// ========== 导出 ==========
window.toggleFabMenu = toggleFabMenu;
window.showUserMenu = showUserMenu;
window.hideUserMenu = hideUserMenu;
window.toggleExpandableMenu = toggleExpandableMenu;
window.switchFabPanel = switchFabPanel;
window.switchConfigPanel = switchConfigPanel;
window.togglePassword = togglePassword;
window.showConfirmModal = showConfirmModal;
window.resetMonitor = resetMonitor;
