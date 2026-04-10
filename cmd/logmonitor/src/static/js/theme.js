// ========== theme.js - 主题管理模块 ==========

/**
 * 主题管理器
 */
const ThemeManager = {
    // 主题列表（6个精选主题）
    themes: [
        'default', 'dark', 'ocean', 'green', 'sunset', 'cyber'
    ],

    // 主题名称映射
    themeNames: {
        'default': '暗夜紫',
        'dark':    '深色模式',
        'ocean':   '深海蓝',
        'green':   '清新绿',
        'sunset':  '暮色橙',
        'cyber':   '科技感霓虹'
    },
    
    /**
     * 获取当前主题
     */
    getCurrentTheme() {
        return localStorage.getItem('currentTheme') || 'default';
    },
    
    /**
     * 设置主题
     * @param {string} themeName - 主题名称
     */
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

    /**
     * 更新主题单选框的选中状态
     * @param {string} themeName - 主题名称
     */
    updateThemeRadioButtons(themeName) {
        const radioButton = document.querySelector(`input[name="theme"][value="${themeName}"]`);
        if (radioButton) {
            radioButton.checked = true;
        }
    },

    /**
     * 初始化主题
     */
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
    },
    
    /**
     * 切换到下一个主题
     */
    toggleNext() {
        const themes = this.themes;
        const current = this.getCurrentTheme();
        const currentIndex = themes.indexOf(current);
        const nextIndex = (currentIndex + 1) % themes.length;
        this.setTheme(themes[nextIndex]);
    },
    
    /**
     * 重置为默认主题
     */
    reset() {
        this.setTheme('default');
    }
};

// ========== 导出到全局 ==========
window.ThemeManager = ThemeManager;
