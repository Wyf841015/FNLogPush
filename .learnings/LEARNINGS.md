# 学习日志

## [LRN-20260407-001] best_practice

**Logged**: 2026-04-07T14:30:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
移动端颜色选择器（input type="color"）无法弹出，需改用预设颜色按钮方案

### Details
- 移动端浏览器对 `<input type="color">` 支持不一致，部分设备点击无反应
- 尝试多种方案：label for 触发、透明覆盖、Bootstrap input-group 等均失败
- 最终采用预设颜色按钮方案：10 个常用颜色，点击直接选择

### Suggested Action
- 颜色选择优先考虑预设方案，移动端兼容性更好
- 预设颜色应包含：蓝、绿、红、黄、青、紫、粉、橙、灰、黑

### Metadata
- Source: user_feedback
- Related Files: cmd/logmonitor/src/templates/index.html, cmd/logmonitor/src/static/js/events_manager.js
- Tags: mobile, ui, color-picker, compatibility
- See Also: LRN-20260407-002

---
## [LRN-20260407-002] best_practice

**Logged**: 2026-04-07T14:35:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
选择颜色时图标颜色应同步联动，提升用户体验

### Details
- 添加事件时，图标预览应跟随选择的颜色变化
- 实现方式：在 selectEventColor 函数中同步更新 event-icon-preview 的 color 样式
- 编辑事件时也需同步显示事件配置的颜色

### Suggested Action
- 颜色相关的 UI 组件应考虑联动反馈
- 选择颜色后实时预览效果，减少用户确认步骤

### Metadata
- Source: user_feedback
- Related Files: cmd/logmonitor/src/static/js/events_manager.js
- Tags: ui, ux, color联动
- See Also: LRN-20260407-001

---
## [LRN-20260407-003] correction

**Logged**: 2026-04-07T15:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
event.target 在某些浏览器上下文可能获取不到正确元素，应先赋值再使用

### Details
- code-review 审查发现直接使用 event.target 可能存在浏览器兼容性问题
- 修正方式：先 `var btn = event.target` 再操作 DOM

### Suggested Action
- 在事件处理函数中，避免直接链式使用 event.target
- 先缓存到变量再使用，提高代码健壮性

### Metadata
- Source: code_review
- Related Files: cmd/logmonitor/src/static/js/events_manager.js
- Tags: javascript, browser-compatibility, code-review

---
## [LRN-20260407-004] knowledge_gap

**Logged**: 2026-04-07T15:30:00+08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
SkillHub 安装后需配置 PATH 环境变量才能使用

### Details
- 安装 SkillHub 后执行 `skillhub search` 报 not found
- 原因：skillhub 安装在 /root/.local/bin/ 但该路径不在 PATH 中
- 解决：使用 `export PATH=$PATH:/root/.local/bin` 或完整路径执行

### Suggested Action
- 文档中应说明安装后需要配置 PATH
- 或使用完整路径调用 skillhub 命令

### Metadata
- Source: error
- Related Files: skillhub 安装
- Tags: skillhub, path, environment

---
## [LRN-20260407-005] knowledge_gap

**Logged**: 2026-04-07T16:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
Bun 重写 Python Flask 项目的可行性评估

### Details
- 用户询问使用 Bun 重写项目的可行性
- 核心挑战：psutil 系统监控库无直接替代方案，需要 Rust 扩展
- 其他功能大部分有 JS 替代：SQLite、bcrypt、socket.io 等
- 飞牛NAS 平台是否支持 Bun 运行时是最大不确定因素

### Suggested Action
- 短期保持 Python 后端，聚焦功能迭代
- 中期可用 Bun 优化前端构建（方案 B）
- 长期若飞牛NAS 支持 Bun 可评估全栈重写

### Metadata
- Source: user_feedback
- Tags: bun, flask, rewrite, feasibility

---
## [LRN-20260407-006] best_practice

**Logged**: 2026-04-07T14:15:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
移动端表格列表应使用 table-responsive 支持横向滚动

### Details
- 移动端事件列表显示不全，只能看到事件 ID
- 原因：表格内容超出屏幕宽度但无滚动容器
- 解决：外层包裹 `<div class="table-responsive">`

### Suggested Action
- 移动端长表格务必使用 table-responsive 包裹
- 考虑使用响应式列隐藏（d-none d-md-table-cell）精简显示

### Metadata
- Source: user_feedback
- Related Files: cmd/logmonitor/src/templates/index.html
- Tags: mobile, responsive, table, ui

---
