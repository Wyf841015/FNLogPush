# Learnings

记录日常工作中学到的经验和教训，用于持续改进。

---

## [LRN-20260418-001] best_practice

**Logged**: 2026-04-18T10:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
统一管理 JavaScript 全局变量，避免重复声明冲突

### Details
在修复 FNOS 日志监控推送系统时，main.js 中声明了 NotificationManager、ThemeManager 等全局变量，与 globals.js 中的声明冲突，导致 "Identifier 'NotificationManager' has already been declared" 错误。

**问题代码：**
```javascript
// globals.js
const NotificationManager = { ... };

// main.js（重复声明）
const NotificationManager = { ... }; // 冲突！
```

### Suggested Action
1. 创建 globals.js 统一管理所有全局变量
2. 确保 HTML 中 globals.js 第一个加载
3. main.js 只包含函数定义，不声明同名全局变量
4. 其他模块文件（session.js、sidebar.js 等）也删除重复的全局变量声明

### Metadata
- Source: error
- Related Files: globals.js, main.js
- Tags: javascript, global-variables, duplicate-declaration
- See Also: LRN-20260418-002

---

## [LRN-20260418-002] best_practice

**Logged**: 2026-04-18T10:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
Fetch API 的 Response 对象 body stream 只能读取一次

### Details
apiFetch 函数中的请求去重逻辑缓存了原始 Promise，导致同一个 Response 对象被多次调用 `.json()`，触发错误：
```
TypeError: Failed to execute 'json' on 'Response': body stream already read
```

**问题代码：**
```javascript
async function apiFetch(url, options = {}) {
    if (pendingRequests.has(url)) {
        return pendingRequests.get(url); // 返回已消费过的 Response
    }
    const fetchPromise = fetch(url, mergedOptions);
    pendingRequests.set(url, fetchPromise);
    // ...
}
```

### Suggested Action
1. 如果需要多次读取 Response，使用 `response.clone()` 创建副本
2. 或者移除请求去重逻辑，让每个调用都创建新的 fetch 请求
3. 对于 API 请求，通常不需要去重，因为数据需要实时性

### Metadata
- Source: error
- Related Files: api.js
- Tags: javascript, fetch, response, stream

---

## [LRN-20260418-003] best_practice

**Logged**: 2026-04-18T11:00:00+08:00
**Priority**: low
**Status**: pending
**Area**: config

### Summary
Python requirements.txt 中不必列出间接依赖

### Details
在检查 requirements.txt 时发现：
- `flask-cors` - 未被代码导入
- `eventlet` - 未使用（Flask-SocketIO 可以不依赖 eventlet 工作）
- `python-socketio` - flask-socketio 的间接依赖
- `python-engineio` - python-socketio 的间接依赖

### Suggested Action
只保留代码中直接 import 的依赖。间接依赖由 pip 自动安装。

**保留的必需依赖：**
- Flask, flask-socketio, psutil, requests, pytz, bcrypt

**可选（推荐但非必需）：**
- python-dotenv, gunicorn

**可移除：**
- flask-cors, eventlet, python-socketio, python-engineio

### Metadata
- Source: conversation
- Tags: python, dependencies, requirements.txt

---

## [LRN-20260418-004] best_practice

**Logged**: 2026-04-18T09:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
修复 JS 文件语法错误应先验证再打包

### Details
在修复 JavaScript 重复声明问题时，通过 `node --check` 验证所有 JS 文件语法：
```bash
for f in *.js; do node --check "$f" && echo "OK $f" || echo "FAIL $f"; done
```

### Suggested Action
1. 修改 JS 文件后，用 `node --check` 验证语法
2. 所有文件通过后再打包
3. 避免打包后发现语法错误需要重新打包

### Metadata
- Source: workflow
- Tags: javascript, syntax-check, build
