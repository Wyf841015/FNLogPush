# Learnings Log

## [LRN-20260420-001] best_practice

**Logged**: 2026-04-20T15:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
前端JS文件中字符串不能包含未转义的换行符，否则导致语法错误

### Details
在 stats.js 中，ECharts 的 formatter 字符串包含未转义的换行符 `\n`：
```javascript
// 错误写法
formatter: "{b}\n{d}%"

// 正确写法
formatter: "{b}: {d}%"
```
这导致浏览器报 `Uncaught SyntaxError: Invalid or unexpected token` 错误。

### Suggested Action
在 JS 文件中使用字符串模板时，避免直接在字符串字面量中使用 `\n`，或者使用模板字符串（反引号）。

### Metadata
- Source: conversation
- Related Files: cmd/logmonitor/src/static/js/stats.js
- Tags: frontend, javascript, syntax

---

## [LRN-20260420-002] best_practice

**Logged**: 2026-04-20T15:35:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
前端调用API前应确认API路径是否正确存在

### Details
前端代码调用 `/api/push/history` API，但该路径不存在，导致返回 404 HTML 页面，前端尝试解析 JSON 时报语法错误。

**错误调用：**
```javascript
var r = await fetch("/api/push/history?limit=1000");
```

**正确做法：**
```javascript
var r = await fetch("/api/stats/chart-data");
```

### Suggested Action
1. 在修改前端代码前，确认后端是否存在对应的 API 路由
2. 使用浏览器的 Network 标签检查 API 响应
3. 添加错误处理，处理 API 返回非 JSON 的情况

### Metadata
- Source: conversation
- Related Files: cmd/logmonitor/src/static/js/stats.js
- Tags: frontend, api, error-handling

---

## [LRN-20260420-003] best_practice

**Logged**: 2026-04-20T16:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: config

### Summary
更新版本号需要同时修改多个文件，保持一致性

### Details
发布新版本时需要更新的文件：
1. `manifest` - 飞牛NAS应用清单
2. `fnpack.json` - FnDepot 应用仓库配置
3. `README.md` - 项目文档（主目录和子目录）
4. `app.py` - 代码中的 `__version__` 变量

### Suggested Action
建立版本更新 checklist：
- [ ] manifest
- [ ] fnpack.json（如果存在）
- [ ] README.md（主目录）
- [ ] README.md（子目录，如果存在）
- [ ] 代码中的版本变量

### Metadata
- Source: conversation
- Tags: version, release, documentation

---

## [LRN-20260420-004] best_practice

**Logged**: 2026-04-20T16:10:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
WebSocket连接失败不应阻塞核心功能，使用轮询作为降级方案

### Details
在生产环境中，WebSocket 可能因 SSL 证书、网络问题等无法连接：
- 直接显示错误日志会干扰用户
- 应该优雅降级到轮询模式

**解决方案：**
```javascript
// 优先使用轮询模式
transports: ['polling', 'websocket']

// 连接失败时降级处理
this.socket.on('connect_error', (error) => {
    console.log('WebSocket连接失败，将使用轮询模式');
    // 不显示错误，不阻塞功能
});
```

### Suggested Action
1. WebSocket 配置优先使用轮询模式
2. 连接失败时静默处理，不显示错误
3. 保留 HTTP 轮询作为备用方案

### Metadata
- Source: conversation
- Related Files: cmd/logmonitor/src/static/js/websocket.js
- Tags: websocket, graceful-degradation, error-handling

---

## [LRN-20260420-005] best_practice

**Logged**: 2026-04-20T16:20:00+08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
GitHub 推送可能因网络问题失败，多次重试通常能成功

### Details
执行 `git push origin master` 时遇到：
- `curl 55 Send failure: Broken pipe`
- `Empty reply from server`
- `Failed to connect to github.com port 443`

等待一段时间后重试通常能成功。

### Suggested Action
1. GitHub 推送失败后，等待 30-60 秒再重试
2. 确保 Git remote URL 包含完整的 token
3. 可以尝试 `git fetch` + `git pull --rebase` 解决冲突后再推送

### Metadata
- Source: conversation
- Tags: git, github, network

---

## [LRN-20260420-006] best_practice

**Logged**: 2026-04-20T16:25:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
JavaScript 文件加载顺序很重要，被依赖的模块必须先加载

### Details
`main.js` 中调用 `initStatsPanel()` 函数，但该函数定义在 `stats.js` 中。如果 `stats.js` 没有正确加载，会报 `ReferenceError: initStatsPanel is not defined`。

### Suggested Action
1. 在 HTML 中确保被依赖的 JS 文件在调用者之前加载
2. 使用浏览器的 Console 和 Network 标签排查加载问题
3. 清除浏览器缓存后再测试

### Metadata
- Source: conversation
- Related Files: cmd/logmonitor/src/templates/index.html
- Tags: javascript, module-loading, dependency

---

## [LRN-20260420-007] best_practice

**Logged**: 2026-04-20T16:30:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
后端 API 应统一返回相同的数据结构，便于前端处理

### Details
项目中不同 API 返回的数据结构不一致：
- 有的返回 `{"success": true, ...}`
- 有的返回 `{"status": "success", ...}`

这导致前端需要针对不同 API 写不同的判断逻辑。

### Suggested Action
1. 制定统一的 API 响应格式规范
2. 创建统一的响应辅助函数
3. 前端添加兼容处理：`if (result.success || result.status === "success")`

### Metadata
- Source: conversation
- Related Files: cmd/logmonitor/src/routes/api_routes.py
- Tags: api, backend, consistency

---

## [LRN-20260421-001] best_practice

**Logged**: 2026-04-21T10:30:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
跨项目复制代码时必须移除对原项目模块的依赖

### Details
从 FnMessageBot 复制 `photo_db_poller.py` 到 log-monitor-fpk 项目时，该文件引用了原项目的模块：
```python
from monitor_core.models import JournalEntry
from monitor_core.sqlite_uri import connect_readonly_with_fallback
```
这些模块在目标项目中不存在，导致应用启动时报错：
```
ModuleNotFoundError: No module named 'monitor_core.models'
```

**正确做法：**
1. 复制代码后立即检查所有 import 语句
2. 将依赖的模块代码一并复制，或用目标项目的等效实现替代
3. 在集成前先测试各模块能否正常导入

### Suggested Action
从 FnMessageBot 复制代码时的检查清单：
- [ ] 列出所有 import 语句
- [ ] 检查每个模块是否存在于目标项目
- [ ] 如不存在，决定复制模块还是用等效实现
- [ ] 测试模块导入：`python -c "from x import y"`

### Metadata
- Source: error
- Related Files: cmd/logmonitor/src/services/photo_db_poller.py
- Tags: code-reuse, import, module-dependency
- See Also: LRN-20260420-001

---

## [LRN-20260421-002] best_practice

**Logged**: 2026-04-21T10:45:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
execute_shell_command 中 heredoc 无法正确处理复杂字符串

### Details
使用 heredoc（`<<`）语法在 shell 命令中写入 Python 代码时，如果内容包含反斜杠、括号等特殊字符，会导致 shell 解析错误：
```
Syntax error: "(" unexpected
```

**问题原因：**
- Heredoc 内容中的 `\`、`()`、`$()` 等会被 shell 预处理
- Python 代码中的类型注解如 `Optional[threading.Thread]` 触发 shell 语法解析

**正确做法：**
1. 使用 `write_file` 工具直接写入文件（避免 shell 解析）
2. 或将文件分成小块写入
3. 或使用 Python 脚本生成文件：`python3 -c "code='...' ; open(f,'w').write(code)"`

### Suggested Action
写入包含复杂语法的代码文件时：
- 优先使用 `write_file` 工具
- 避免 heredoc 中写入带复杂语法的内容
- 大文件可分多次写入

### Metadata
- Source: error
- Tags: shell, heredoc, execute_shell_command, python

---

## [LRN-20260421-003] best_practice

**Logged**: 2026-04-21T11:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
危险命令需要用户审批，超时不响应会导致操作失败

### Details
执行 `rm -f /app/working/workspaces/default/project/log-monitor-fpk/cmd/logmonitor/src/services/photo_db_poller.py` 时被安全系统拦截，需要用户输入 `/approve` 审批。用户未在超时时间内响应，导致命令被拒绝。

### Suggested Action
1. 涉及删除文件等危险操作时，先说明操作风险
2. 等待用户确认后再执行
3. 可提供替代方案（如用空文件覆盖）

### Metadata
- Source: error
- Tags: tool-approval, dangerous-command, timeout

---

## [LRN-20260421-004] best_practice

**Logged**: 2026-04-21T11:15:00+08:00
**Priority**: medium
**Status**: pending
**Area**: workflow

### Summary
修复应用启动问题的正确流程

### Details
修复依赖模块问题的标准流程：
1. **测试导入**：`python -c "import module"` 检查模块是否存在
2. **定位问题**：查看报错堆栈，找出缺失的 import
3. **修复或替换**：移除不可用的 import，用标准库替代
4. **验证修复**：重新测试模块导入
5. **测试启动**：启动应用确认无错误

**避免跳过步骤**：不能假设修复后就能工作，必须逐项验证。

### Suggested Action
遇到 "Module not found" 错误时：
1. 先运行 `python -c "import xxx"` 确认问题
2. 检查 import 语句，移除不可用的依赖
3. 使用标准库替代（如用 `sqlite3` 替代自定义的 `sqlite_uri`）
4. 再次测试导入
5. 最后测试完整应用启动

### Metadata
- Source: conversation
- Tags: debugging, import, workflow

---
