// ========== auth.js - 认证模块 ==========

// ========== 检查会话 ==========

function checkSession() {
    apiFetch('/api/auth/status')
        .then(response => response.json())
        .then(data => {
            if (data.authenticated) {
                const usernameEl = document.getElementById('username-display');
                if (usernameEl) usernameEl.textContent = data.username || 'Admin';
            } else {
                window.location.href = '/login';
            }
        })
        .catch(() => {
            window.location.href = '/login';
        });
}

// ========== 修改密码 ==========

function showChangePasswordModal() {
    const modal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
    modal.show();
}

function hideChangePasswordModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('changePasswordModal'));
    if (modal) modal.hide();
    const form = document.getElementById('changePasswordForm');
    if (form) form.reset();
}

function showChangePasswordAlert(message, type) {
    const alertEl = document.getElementById('changePasswordAlert');
    if (!alertEl) return;
    
    alertEl.className = `alert alert-${type} mt-3`;
    alertEl.textContent = message;
    alertEl.style.display = 'block';
    
    setTimeout(() => {
        alertEl.style.display = 'none';
    }, 5000);
}

async function changePassword() {
    const currentPassword = document.getElementById('currentPassword')?.value;
    const newPassword = document.getElementById('newPassword')?.value;
    const confirmPassword = document.getElementById('confirmPassword')?.value;
    
    if (!currentPassword || !newPassword || !confirmPassword) {
        showChangePasswordAlert('请填写所有字段', 'warning');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showChangePasswordAlert('新密码与确认密码不匹配', 'warning');
        return;
    }
    
    if (newPassword.length < 6) {
        showChangePasswordAlert('新密码长度至少6位', 'warning');
        return;
    }
    
    try {
        const response = await apiFetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        const data = await response.json();
        
        if (data.success) {
            showChangePasswordAlert('密码修改成功！', 'success');
            setTimeout(() => {
                hideChangePasswordModal();
            }, 1500);
        } else {
            showChangePasswordAlert(data.error || '密码修改失败', 'danger');
        }
    } catch (e) {
        showChangePasswordAlert('请求失败: ' + e.message, 'danger');
    }
}

// ========== 导出 ==========
window.checkSession = checkSession;
window.showChangePasswordModal = showChangePasswordModal;
window.hideChangePasswordModal = hideChangePasswordModal;
window.showChangePasswordAlert = showChangePasswordAlert;
window.changePassword = changePassword;
