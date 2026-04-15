# 学习记录

## [LRN-20260408-001] best_practice

**Logged**: 2026-04-08T18:27:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
FPK 打包的 Python 项目中，加密密钥必须在安装时预生成并持久化存储

### Details
推送渠道配置（如 Webhook URL）使用 Fernet AES 加密存储。问题是每次应用重启时，如果加密密钥丢失或位置变化，已加密的配置将无法解密。

原因分析：
1. 加密密钥最初保存在 `APP_HOME/config/.encrypt_key`
2. 安装时未预生成密钥
3. Python 代码依赖 `APP_HOME` 环境变量，但该变量可能不可用

### Suggested Action
修复方案：
1. **install_callback**: 安装时用 Python 生成密钥并保存到 `${TRIM_PKGVAR}/config/.encrypt_key`
2. **upgrade_callback**: 升级时保留已有密钥
3. **crypto.py**: 改进密钥存储逻辑，支持多个备用路径（TRIM_PKGVAR > APP_HOME > ~/.fnlogpush）

### Metadata
- Source: user_feedback
- Related Files:
  - cmd/install_callback
  - cmd/upgrade_callback
  - cmd/logmonitor/src/utils/crypto.py
- Tags: encryption, fpk, persistence

---

## [LRN-20260408-002] best_practice

**Logged**: 2026-04-08T18:27:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
JavaScript 中存在重复函数定义时，后定义的函数会覆盖先定义的，可能导致意外行为

### Details
代码中存在两个 `switchFabPanel` 函数：
- 第 516 行：正确处理了移动端底部导航 active 状态
- 第 2164 行：缺少移动端导航处理

由于 JavaScript 函数提升，后定义的函数生效，导致移动端导航状态不同步。

### Suggested Action
1. 避免重复函数定义，使用有意义的命名区分
2. 代码审查时检查是否存在函数重复
3. 考虑合并重复函数或删除旧版本

### Metadata
- Source: user_feedback
- Related Files:
  - cmd/logmonitor/src/static/js/main.js
- Tags: javascript, code-duplication, mobile-nav

---

## [LRN-20260408-003] best_practice

**Logged**: 2026-04-08T18:27:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
第三方 API 状态码判断需要兼容多种响应格式和字段名

### Details
MeoW 推送 API 返回的状态字段可能是 `status` 或 `code`，而状态码含义：
- 200: 操作成功
- 400: 参数错误
- 500: 服务器错误
- data=False: 也表示失败

原代码只检查 `result.get('status') != 200`，导致状态判断不准确。

### Suggested Action
修复方案：
```python
status_code = result.get('code') or result.get('status')
if status_code == 200:
    if result.get('data') is not False:
        # 成功
    else:
        # 失败 (data=False)
elif status_code == 400:
    # 参数错误
elif status_code == 500:
    # 服务器错误
```

### Metadata
- Source: user_feedback
- Related Files:
  - cmd/logmonitor/src/services/push_service.py (MeoWPushChannel.push)
- Tags: api-integration, error-handling, meow

---

## [LRN-20260408-004] best_practice

**Logged**: 2026-04-08T23:22:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
FPK 应用版本更新需要同步多个仓库和文件

### Details
发布新版本时需要更新的文件：
1. **FNLogPush 仓库**:
   - manifest (version)
   - README.md (version + changelog)
   - cmd/install_callback (如有必要)
   - cmd/upgrade_callback (如有必要)

2. **FnDepot 仓库**:
   - fnpack.json (version + changelog)
   - fnlogpush/README.md (version + changelog)
   - fnlogpush/fnlogpush.fpk (编译后的安装包)

3. **Git 推送**:
   - GitHub 和 Gitee 都需要推送

### Suggested Action
建议使用脚本自动化版本更新流程，或创建版本更新清单 checklist。

### Metadata
- Source: conversation
- Related Files:
  - project/log-monitor-fpk/
  - project/FnDepot/
- Tags: versioning, release, multi-repo

---

## [LRN-20260408-005] best_practice

**Logged**: 2026-04-08T23:22:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
Git push 超时或 GnuTLS 错误时，多次重试通常可以成功

### Details
网络不稳定时 git push 会失败：
- GnuTLS recv error (-110)
- Failed to connect to github.com port 443
- Timeout

### Suggested Action
遇到网络错误时，等待几秒后重试，通常 2-3 次可以成功。

### Metadata
- Source: conversation
- Related Files:
- Tags: git, networking, troubleshooting

---

## [LRN-20260415-001] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
Heredoc 向 JavaScript 文件追加内容时，花括号会被 shell 解析导致语法错误

### Details
尝试使用 `cat >> main.js << EOF` 追加代码时，shell 将 `{}` 解释为子 shell，导致语法错误：
```
Syntax error: "}" unexpected
```

### Suggested Action
追加代码到 JS 文件时使用以下方法之一：
1. 使用 `write_file` 写入临时文件，然后用 `cat` 合并
2. 使用 Python 写入文件
3. 避免 heredoc，改用 echo 逐行追加

### Metadata
- Source: error
- Related Files:
  - project/log-monitor-fpk/cmd/logmonitor/src/static/js/main.js
- Tags: shell, javascript, heredoc, syntax-error
- See Also: LRN-20260408-002

---

## [LRN-20260415-002] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
从参考项目同步代码时必须使用绝对路径，相对路径可能因 cwd 不同而失败

### Details
执行 `cp project/log-monitor-fpk1/.../main.js` 失败，但 `cp /app/working/workspaces/default/project/log-monitor-fpk1/.../main.js` 成功。

原因：工作目录可能不是预期的位置，相对路径解析错误。

### Suggested Action
同步参考项目代码时使用绝对路径：
```bash
cp /app/working/workspaces/default/project/log-monitor-fpk1/cmd/logmonitor/src/static/js/main.js cmd/logmonitor/src/static/js/main.js
```

### Metadata
- Source: error
- Related Files:
  - project/log-monitor-fpk/
- Tags: shell, path, file-copy

---

## [LRN-20260415-003] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
模块化 JS 架构与 HTML onclick 兼容性问题：函数必须导出到 window 对象

### Details
HTML 中的 `onclick="functionName()"` 需要函数存在于全局作用域。模块化 JS 使用 ES6 `import/export` 或 IIFE 封装时，函数默认不在 window 上。

解决方案：
```javascript
// 模块内定义
function myFunction() { ... }

// 导出到全局
window.myFunction = myFunction;
```

### Suggested Action
1. 所有被 HTML onclick 调用的函数必须 `window.xxx = xxx`
2. 开发时检查 HTML 调用的函数是否都在 window 上
3. 写 Python 脚本自动检查 HTML onClick 函数定义

### Metadata
- Source: conversation
- Related Files:
  - project/log-monitor-fpk/cmd/logmonitor/src/templates/index.html
- Tags: javascript, window-export, onclick

---

## [LRN-20260415-004] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
面板切换时必须调用数据加载函数，否则 UI 无数据刷新无反应

### Details
修复菜单无反应问题时发现，`switchNavPanel` 函数只切换了面板显示，但未加载数据。用户点击菜单后看到空白面板，以为功能坏了。

原因：`loadPanelData()` 函数存在但未被调用。

### Suggested Action
1. `switchNavPanel` 函数切换面板时应调用 `loadPanelData(panelId)`
2. 每个面板数据加载函数需要注册到映射表
3. 添加数据加载状态指示（loading spinner）

### Metadata
- Source: error
- Related Files:
  - project/log-monitor-fpk/cmd/logmonitor/src/static/js/main.js
- Tags: ui-ux, panel-switch, data-loading

---

## [LRN-20260415-005] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
页面无限刷新问题：缺少 API 接口时前端轮询会陷入错误处理死循环

### Details
页面加载后不断刷新，F12 发现：
1. `/api/auth/status` 返回 404 → 触发刷新
2. `/api/agg/stats` 返回 404 → 触发刷新

错误处理代码在接口失败时触发页面刷新，但接口不存在导致无限循环。

### Suggested Action
1. 前端轮询要有退避策略（指数退避）
2. 接口 404 时停止轮询，提示用户而非自动刷新
3. 确保后端实现了所有前端调用的接口

### Metadata
- Source: error
- Related Files:
  - project/log-monitor-fpk/cmd/logmonitor/src/static/js/main.js
- Tags: api, polling, infinite-loop, refresh

---

## [LRN-20260415-006] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
JavaScript 正则表达式中字符串拼接时 `$&` 需要正确转义

### Details
在 `replace()` 回调中构建正则表达式时：
```javascript
// 错误：\$& 会被解析
pattern = new RegExp('\\b' + key.replace(/[.*+?^${}()|[\]\\]/g, '\$&') + '\\b');

// 正确：直接用 $&
pattern = new RegExp('\\b' + key.replace(/[.*+?^${}()|[\]\\]/g, '$&') + '\\b');
```

`\$&` 在 JavaScript 字符串中不是有效转义序列。

### Suggested Action
1. 记住 `$&` 在 replace 回调中是特殊字符，代表匹配内容
2. 在普通字符串拼接中不需要转义
3. 使用 `node --check` 验证 JS 语法

### Metadata
- Source: error
- Related Files:
  - project/log-monitor-fpk/cmd/logmonitor/src/static/js/history.js
- Tags: javascript, regex, string-escape

---

## [LRN-20260415-007] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: low
**Status**: resolved
**Area**: frontend

### Summary
模块化 vs 单文件架构选择：参考项目使用 134KB 单文件 main.js

### Details
对比参考项目与当前项目的 JS 架构：

| 维度 | 参考项目 | 当前项目 |
|------|----------|----------|
| 文件数 | 1 个 main.js (134KB) | 16 个模块化 JS |
| 维护性 | 差 | 好 |
| 功能完整性 | 完整 | 需同步 |

参考项目虽然文件大，但功能完整，函数间调用无障碍。

### Suggested Action
对于中小型项目，可考虑：
1. 模块化开发便于维护
2. 构建时合并压缩
3. 或直接同步参考项目完整代码

### Metadata
- Source: conversation
- Related Files:
  - project/log-monitor-fpk1/cmd/logmonitor/src/static/js/main.js
- Tags: architecture, code-organization, frontend

---

## [LRN-20260415-008] best_practice

**Logged**: 2026-04-15T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
全面 JS 语法检查后打包，确保所有代码无语法错误

### Details
使用 `node --check` 批量检查所有 JS 文件：
```bash
for f in cmd/logmonitor/src/static/js/*.js; do
    node --check "$f" || echo "❌ $f"
done
```

发现问题：
- main.js 语法错误（意外的文件末尾）
- bootstrap.bundle.min.js 和 socket.io.min.js 是压缩文件，node 检查会报错

### Suggested Action
1. 批量检查命令加入 Makefile 或 npm script
2. 排除 .min.js 文件
3. 语法检查通过后再打包

### Metadata
- Source: conversation
- Related Files:
  - project/log-monitor-fpk/cmd/logmonitor/src/static/js/*.js
- Tags: code-quality, syntax-check, node

---

## [LRN-20260416-001] best_practice

**Logged**: 2026-04-16T14:30:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
定时任务执行时遇到工具不可用问题，需要检查 tool call 格式

### Details
执行定时新闻推送任务时，工具调用失败：
```
FunctionNotFoundError: Cannot find the function named execute_shell_command
```

原因可能是工具名称写错或工具加载问题。重新发送消息后工具恢复正常。

### Suggested Action
1. 遇到工具不可用时重新发送请求
2. 确认工具名称拼写正确
3. 检查 agent 配置是否正确加载工具

### Metadata
- Source: error
- Related Files:
- Tags: cron, tool, agent

---

## [LRN-20260416-002] best_practice

**Logged**: 2026-04-16T14:35:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
第三方 API 调用需要查看文档确定正确的接口格式

### Details
推送军事新闻到方糖 API 时遇到问题：
1. 直接 GET 请求 URL 路径格式失败（404 Not Found）
2. 尝试 /send 接口需要 channelId 参数，但填错昵称导致 IP 被封禁
3. 最终使用 /push 接口 POST JSON 格式成功

### Suggested Action
1. 不确定 API 格式时先查看文档
2. 测试不同接口尝试时注意频率限制
3. 优先使用 POST + JSON 格式，比 URL 参数更安全

### Metadata
- Source: error
- Related Files:
- Tags: api, http, troubleshooting, third-party

---

## [LRN-20260416-003] best_practice

**Logged**: 2026-04-16T14:40:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
Git rebase 遇到冲突时可以使用 --theirs 或 --ours 选择版本

### Details
执行 `git pull --rebase` 时遇到冲突：
```
error: Pulling is not possible because you have unmerged files.
Unmerged paths: both modified: .learnings/LEARNINGS.md
```

解决方法：
```bash
git checkout --theirs .learnings/LEARNINGS.md  # 使用远程版本
git add .learnings/LEARNINGS.md
git commit -m "message"
git rebase --continue
```

### Suggested Action
1. Rebase 冲突时快速解决：使用 --theirs 接受远程版本
2. 如果需要保留本地修改，手动编辑文件解决冲突
3. 解决后记得 `git add` 标记已解决

### Metadata
- Source: error
- Related Files:
  - project/log-monitor-fpk/.learnings/LEARNINGS.md
- Tags: git, rebase, conflict-resolution
 