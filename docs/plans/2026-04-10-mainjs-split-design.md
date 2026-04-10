# main.js 拆分计划

## 目标
将 2857 行的 main.js 拆分为多个功能模块，提升可维护性。

## 拆分结构

```
static/js/
├── main.js              # 入口文件 (~300行)
├── api.js               # API请求 (~100行) ✅ 已有
├── websocket.js         # WebSocket (~150行) ✅ 已有
├── components.js        # UI组件 (~175行) ✅ 已有
├── sidebar.js           # 侧边栏导航 (~100行) 🆕
├── session.js           # Session管理 (~150行) 🆕
├── health.js            # 健康状态监控 (~200行) 🆕
├── theme.js             # 主题管理 (~200行) 🆕
├── history.js           # 历史记录 (~400行) 🆕
├── config.js            # 配置管理 (~400行) 🆕
├── fab.js               # FAB浮动按钮 (~150行) 🆕
├── auth.js              # 认证相关 (~150行) 🆕
├── stats.js             # 统计/聚合 (~100行) 🆕
└── utils.js             # 工具函数 (~150行) 🆕
```

## 模块划分详情

### 1. utils.js - 工具函数
- eventCategoriesCache / loadEventCategoriesFromAPI
- CONSTANTS
- formatRelativeTime
- escapeHtml
- showNotification
- debounce / throttle (从 api.js 移动)
- highlightKeyword
- animateNumber

### 2. sidebar.js - 侧边栏
- sidebarOpen / sidebarCollapsed
- toggleSidebar
- closeSidebar
- toggleSidebarCollapse
- switchNavPanel
- syncNavActive

### 3. session.js - Session管理
- sessionCheckInterval / activityRefreshInterval
- lastActivityTime
- setupActivityDetection
- startSessionCheck
- NotificationManager
- testNotification
- healthUpdateInterval
- loadHealthStatus
- updateHealthStatusData
- updateHealthStatus
- startHealthUpdate
- stopHealthUpdate

### 4. health.js - 健康状态（从session.js分离）
- loadBackupDbStatus
- checkAndRefreshHistory
- showNewPushNotification
- ThemeManager
- loadStatus
- ThemeManager.toggle / ThemeManager.save / ThemeManager.load

### 5. history.js - 历史记录
- lastHistoryIndex
- _historySearchTimer
- onHistorySearch
- historyKeyword / historyCurrentPage / historyTotal
- loadHistory
- updatePaginationControls
- prevPage / nextPage
- showHistoryDetail
- refreshHistory
- checkDatabaseFull / checkDatabase
- historyDateFilter
- onHistoryDateFilter
- clearHistoryDateFilter
- initHistoryDateFilter

### 6. config.js - 配置管理
- controlMonitor
- togglePassword
- showConfirmModal
- resetMonitor
- selectAllInCategory / deselectAllInCategory
- testWebhook
- saveBasicConfig
- savePushConfig
- saveFilterConfig
- saveThemeConfig
- saveBackupConfig
- testBackupDbConnection
- checkDatabaseFull

### 7. fab.js - FAB浮动按钮
- toggleFabMenu
- showUserMenu / hideUserMenu
- toggleExpandableMenu
- switchFabPanel
- switchConfigPanel

### 8. auth.js - 认证相关
- showChangePasswordModal
- hideChangePasswordModal
- showChangePasswordAlert
- checkDatabase (移动到 auth.js)

### 9. stats.js - 统计/聚合
- loadAggStats

### 10. main.js - 入口文件（精简后）
- 全局常量定义
- DOMContentLoaded 初始化
- 导入各模块

## HTML 更新

需要更新 index.html 中的脚本引用顺序：

```html
<!-- 基础工具模块 -->
<script src="{{ url_for('static', filename='js/api.js') }}"></script>
<script src="{{ url_for('static', filename='js/websocket.js') }}"></script>
<script src="{{ url_for('static', filename='js/components.js') }}"></script>

<!-- 业务模块（按依赖顺序） -->
<script src="{{ url_for('static', filename='js/utils.js') }}"></script>
<script src="{{ url_for('static', filename='js/sidebar.js') }}"></script>
<script src="{{ url_for('static', filename='js/session.js') }}"></script>
<script src="{{ url_for('static', filename='js/health.js') }}"></script>
<script src="{{ url_for('static', filename='js/theme.js') }}"></script>
<script src="{{ url_for('static', filename='js/history.js') }}"></script>
<script src="{{ url_for('static', filename='js/config.js') }}"></script>
<script src="{{ url_for('static', filename='js/fab.js') }}"></script>
<script src="{{ url_for('static', filename='js/auth.js') }}"></script>
<script src="{{ url_for('static', filename='js/stats.js') }}"></script>
<script src="{{ url_for('static', filename='js/events_manager.js') }}"></script>

<!-- 主入口（最后加载） -->
<script src="{{ url_for('static', filename='js/main.js') }}"></script>
```

## 实施步骤

### 步骤 1: 创建 utils.js
- 提取工具函数
- 测试功能正常

### 步骤 2: 创建 sidebar.js
- 提取侧边栏相关函数
- 测试侧边栏交互正常

### 步骤 3: 创建 session.js + health.js
- 分离 session 和 health 模块
- 测试状态更新正常

### 步骤 4: 创建 theme.js
- 提取 ThemeManager
- 测试主题切换正常

### 步骤 5: 创建 history.js
- 提取历史记录相关函数
- 测试分页、搜索正常

### 步骤 6: 创建 config.js
- 提取配置保存函数
- 测试配置保存正常

### 步骤 7: 创建 fab.js
- 提取 FAB 菜单函数
- 测试菜单交互正常

### 步骤 8: 创建 auth.js
- 提取认证相关函数
- 测试登录、修改密码正常

### 步骤 9: 创建 stats.js
- 提取统计函数
- 测试聚合统计正常

### 步骤 10: 精简 main.js
- 保留入口代码和初始化
- 删除已分离的函数

### 步骤 11: 更新 index.html
- 更新脚本引用顺序
- 添加新模块引用

### 步骤 12: 全面测试
- 测试所有功能正常
- 验证日志正常输出
