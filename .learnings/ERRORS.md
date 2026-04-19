# Errors Log

## [ERR-20260420-001] stats.js syntax error

**Logged**: 2026-04-20T14:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
stats.js 语法错误，未转义的换行符导致页面无法加载

### Error
```
Uncaught SyntaxError: Invalid or unexpected token (at stats.js:427:49)
```

### Context
- 在 stats.js 的 ECharts formatter 配置中使用了未转义的换行符
- `{b}\n{d}%` 导致 JS 解析失败

### Suggested Fix
```javascript
// 错误
formatter: "{b}\n{d}%"

// 正确
formatter: "{b}: {d}%"
```

### Metadata
- Reproducible: yes
- Related Files: cmd/logmonitor/src/static/js/stats.js:427
- See Also: LRN-20260420-001

---

## [ERR-20260420-002] API 404 Not Found

**Logged**: 2026-04-20T14:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
前端调用不存在的 API `/api/push/history`

### Error
```
GET https://fnlogpush.64652178.xyz:16607/api/push/history?limit=1000 404 (Not Found)
loadStatsOverview error SyntaxError: Unexpected token '<', "<!doctype "... is not valid JSON
```

### Context
- loadStatsOverview 函数调用了错误的 API 路径
- 返回 404 HTML 页面，前端尝试解析为 JSON 失败

### Suggested Fix
使用正确的 API 路径 `/api/stats/chart-data`

### Metadata
- Reproducible: yes
- Related Files: cmd/logmonitor/src/static/js/stats.js
- See Also: LRN-20260420-002

---

## [ERR-20260420-003] GitHub push connection failure

**Logged**: 2026-04-20T16:15:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
GitHub 推送时网络连接不稳定

### Error
```
error: RPC failed; curl 55 Send failure: Broken pipe
fatal: the remote end hung up unexpectedly

error: could not read Password for 'https://github.com/...': No such device or address

fatal: unable to access 'https://github.com/...': Failed to connect to github.com port 443
```

### Context
- 执行 `git push origin master` 时遇到网络问题
- 可能与代理设置、网络波动有关
- 多次重试后最终成功

### Suggested Fix
1. 等待 30-60 秒后重试
2. 确保 Git remote URL 包含完整的 personal access token
3. 检查网络代理设置

### Metadata
- Reproducible: uncertain
- See Also: LRN-20260420-005

---

## [ERR-20260420-004] WebSocket SSL connection error

**Logged**: 2026-04-20T14:45:00+08:00
**Priority**: low
**Status**: wont_fix
**Area**: frontend

### Summary
WebSocket 连接因 SSL 证书问题失败

### Error
```
WebSocket connection to 'wss://fnlogpush.64652178.xyz:16607/socket.io/?EIO=4&transport=websocket' failed: Invalid frame header
```

### Context
- SSL 证书配置问题导致 WebSocket 无法建立
- 错误信息在控制台持续显示，影响用户体验

### Suggested Fix
- 改用轮询模式作为降级方案（已实施）
- 不阻塞核心功能，静默处理错误

### Metadata
- Reproducible: yes
- Related Files: cmd/logmonitor/src/static/js/websocket.js
- See Also: LRN-20260420-004

---
