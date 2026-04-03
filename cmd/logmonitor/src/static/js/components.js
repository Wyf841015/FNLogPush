// ========== UI 组件模块 ==========

// Toast 通知组件
const Toast = {
    container: null,

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            this.container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info', duration = 3000) {
        this.init();

        const toast = document.createElement('div');
        toast.className = `toast show align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        this.container.appendChild(toast);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
    info(message) { this.show(message, 'info'); },
    warning(message) { this.show(message, 'warning'); }
};

// 确认对话框
const ConfirmDialog = {
    show(options) {
        return new Promise((resolve) => {
            const { title = '确认', message = '确定要执行此操作吗？', confirmText = '确定', cancelText = '取消', danger = false } = options;

            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                            <button type="button" class="btn ${danger ? 'btn-danger' : 'btn-primary'} btn-confirm">${confirmText}</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);

            modal.querySelector('.btn-confirm').addEventListener('click', () => {
                bsModal.hide();
                resolve(true);
            });

            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
                resolve(false);
            });

            bsModal.show();
        });
    }
};

// Skeleton Loader
const Skeleton = {
    create(type = 'card') {
        const templates = {
            card: `<div class="card skeleton-card"><div class="card-body"><div class="skeleton skeleton-text w-75"></div><div class="skeleton skeleton-text w-50"></div></div></div>`,
            row: `<div class="d-flex align-items-center mb-2"><div class="skeleton me-2" style="width:40px;height:40px;border-radius:50%;"></div><div class="flex-grow-1"><div class="skeleton skeleton-text w-75"></div><div class="skeleton skeleton-text w-50"></div></div></div>`,
            table: `<tr><td><div class="skeleton skeleton-text w-100"></div></td><td><div class="skeleton skeleton-text w-75"></div></td><td><div class="skeleton skeleton-text w-50"></div></td></tr>`
        };

        const style = document.createElement('style');
        style.textContent = `
            .skeleton { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200% 100%; animation: skeleton-loading 1.5s infinite; }
            @keyframes skeleton-loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
            .dark .skeleton { background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%); background-size: 200% 100%; }
            .theme-dark .skeleton { background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%); background-size: 200% 100%; }
            .skeleton-text { height: 1em; border-radius: 4px; margin-bottom: 0.5em; }
            .skeleton-card { padding: 1rem; margin-bottom: 1rem; }
        `;
        if (!document.querySelector('style[data-id="skeleton"]')) {
            style.setAttribute('data-id', 'skeleton');
            document.head.appendChild(style);
        }

        return templates[type] || templates.card;
    }
};

// 虚拟滚动（简化版）
class VirtualList {
    constructor(options) {
        this.container = options.container;
        this.itemHeight = options.itemHeight || 50;
        this.items = options.items || [];
        this.renderItem = options.renderItem || ((item) => item.toString());
        this.bufferSize = options.bufferSize || 5;

        this.scrollTop = 0;
        this.visibleCount = 0;
        this.init();
    }

    init() {
        this.container.style.overflow = 'auto';
        this.container.style.position = 'relative';

        this.content = document.createElement('div');
        this.content.style.position = 'relative';
        this.container.appendChild(this.content);

        this.container.addEventListener('scroll', throttle(() => {
            this.scrollTop = this.container.scrollTop;
            this.render();
        }, 16));
    }

    setItems(items) {
        this.items = items;
        this.content.style.height = `${items.length * this.itemHeight}px`;
        this.render();
    }

    render() {
        const containerHeight = this.container.clientHeight;
        this.visibleCount = Math.ceil(containerHeight / this.itemHeight) + this.bufferSize * 2;

        const startIndex = Math.max(0, Math.floor(this.scrollTop / this.itemHeight) - this.bufferSize);
        const endIndex = Math.min(this.items.length, startIndex + this.visibleCount);

        // 清除现有项
        const existingItems = this.content.querySelectorAll('.vlist-item');
        existingItems.forEach(el => el.remove());

        // 渲染可见项
        for (let i = startIndex; i < endIndex; i++) {
            const item = this.items[i];
            const el = document.createElement('div');
            el.className = 'vlist-item';
            el.style.cssText = `position:absolute;top:${i * this.itemHeight}px;left:0;right:0;height:${this.itemHeight}px;`;
            el.innerHTML = this.renderItem(item, i);
            this.content.appendChild(el);
        }
    }
}

// 导出组件
window.Toast = Toast;
window.ConfirmDialog = ConfirmDialog;
window.Skeleton = Skeleton;
window.VirtualList = VirtualList;
