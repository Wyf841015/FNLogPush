# Learnings Log

## [LRN-20260406-001] best_practice

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
移动端遮罩层需要同时设置 opacity 和 pointer-events 才能禁用点击穿透

### Details
在为侧边栏遮罩层 `.sidebar-overlay` 设置 `display: none` 时，虽然视觉上隐藏了，但元素仍然能接收点击事件。需要额外设置 `pointer-events: none` 才能禁用点击。

### Suggested Action
CSS 遮罩层应该同时设置：
```css
.sidebar-overlay {
    opacity: 0;
    pointer-events: none;  /* 禁用点击 */
}
.sidebar-overlay.active {
    opacity: 1;
    pointer-events: auto;  /* 启用点击 */
}
```

### Metadata
- Source: user_feedback
- Related Files: cmd/logmonitor/src/static/css/themes.css
- Tags: mobile, css, pointer-events
- Pattern-Key: frontend.overlay.click_through

---

## [LRN-20260406-002] best_practice

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
JavaScript 中重复定义函数会导致后定义的覆盖先定义的

### Details
在 main.js 中，`toggleSidebar()` 函数被定义了两次：
- 第30行：正确的侧边栏切换逻辑
- 第2150行：旧的 `toggleFabMenu()` 调用

后定义的函数会覆盖先定义的，导致正确的逻辑被覆盖。

### Suggested Action
1. 删除重复的旧函数定义
2. 代码审查时注意检查函数重名情况
3. 使用 ESLint 等工具检测未使用的函数

### Metadata
- Source: user_feedback
- Related Files: cmd/logmonitor/src/static/js/main.js
- Tags: javascript, function-override, debugging

---

## [LRN-20260406-003] correction

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
移动端底部导航栏点击事件监听器是多余的

### Details
最初添加了额外的 JavaScript 事件监听器来同步底部导航的 active 状态，但由于 onclick 已经正确工作，这个监听器导致了行为异常。

### Suggested Action
移除多余的事件监听器，依赖 HTML onclick 属性：
```javascript
// 不需要额外的监听器
// onclick="switchNavPanel(this, 'status')" 已足够
```

### Metadata
- Source: conversation
- Related Files: cmd/logmonitor/src/templates/index.html
- Tags: mobile-nav, event-listener

---

## [LRN-20260406-004] best_practice

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
Git 二进制文件冲突需要手动解决，rebase 方式会产生更多冲突

### Details
使用 `git pull --rebase` 时，二进制文件（如图标 PNG）无法自动合并，产生冲突。直接 `git push --force` 可以覆盖远程版本。

### Suggested Action
1. 图标等二进制文件应一次性更新到位
2. 避免对二进制文件进行 rebase
3. 必要时使用 `--force` 推送（需确保本地版本正确）

### Metadata
- Source: error
- Related Files: ICON*.PNG
- Tags: git, binary-files, force-push

---

## [LRN-20260406-005] knowledge_gap

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
SkillHub CLI 安装后需要添加到 PATH 才能使用

### Details
使用 curl 安装 SkillHub CLI 后，命令 `skillhub` 无法直接执行，需要手动添加 `/root/.local/bin` 到 PATH 环境变量。

### Suggested Action
安装后立即验证并添加到 PATH：
```bash
export PATH="$PATH:/root/.local/bin"
skillhub install <skill-name>
```

### Metadata
- Source: error
- Tags: skillhub, path, installation

---

## [LRN-20260406-006] best_practice

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
PIL 生成的图标需要验证是否有实际内容

### Details
使用 Python PIL 库生成图标后，文件大小正常但显示为空。可能是绘制操作没有正确执行或图层顺序问题。

### Suggested Action
生成图标后验证内容：
```python
from PIL import Image
img = Image.open('icon.png')
alpha = img.split()[3]
non_transparent = sum(1 for p in alpha.getdata() if p > 0)
print(f'Non-transparent pixels: {non_transparent}')
```
像素数应大于 0 才表示有内容。

### Metadata
- Source: user_feedback
- Related Files: generate_icon.py
- Tags: python, pil, image-generation
- Pattern-Key: image.generation.verify

---

## [LRN-20260406-007] correction

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: frontend

### Summary
移动端侧边栏默认隐藏是 CSS 控制的，不是 JS

### Details
最初怀疑是 JavaScript 问题导致侧边栏无法隐藏/弹出，实际上 CSS 的 `transform: translateX(-100%)` 已经正确控制默认隐藏状态。问题出在重复的函数定义。

### Suggested Action
排查问题时先确认基础 CSS 是否正确，再检查 JavaScript。

### Metadata
- Source: conversation
- Related Files: cmd/logmonitor/src/static/css/themes.css
- Tags: mobile-sidebar, css-transform

---
