# 错误记录

## [ERR-20260408-001] git-push-timeout

**Logged**: 2026-04-08T23:22:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
Git push 到 GitHub 超时或 TLS 连接错误

### Error
```
fatal: unable to access 'https://github.com/...': GnuTLS recv error (-110): The TLS connection was non-properly terminated.
fatal: unable to access 'https://github.com/...': Failed to connect to github.com port 443 after 134582 ms: Couldn't connect to server
```

### Context
- 推送 FNLogPush 和 FnDepot 仓库
- 网络不稳定
- 超时时间 60-180 秒

### Suggested Fix
多次重试 git push 命令，通常 2-3 次可以成功

### Metadata
- Reproducible: sometimes
- Related Files:
- See Also: LRN-20260408-005

---

## [ERR-20260411-001] fnpack-manifest-missing

**Logged**: 2026-04-11T22:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
fnpack 打包失败，找不到 manifest 文件

### Error
```
Verifying files...
error: pathspec 'manifest' did not match any file(s) known to git
```

### Context
- git commit 时 manifest 文件被重命名为 manifest.txt
- fnpack 工具期望的文件名是 "manifest"

### Suggested Fix
```bash
git show HEAD:manifest > manifest
```

### Metadata
- Reproducible: yes
- Related Files:
  - project/log-monitor-fpk/manifest
- See Also: LRN-20260411-002

---

## [ERR-20260411-002] page-infinite-refresh

**Logged**: 2026-04-11T22:30:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: frontend

### Summary
登录后页面无限刷新

### Error
页面持续刷新，无法正常使用

### Context
1. session.js 调用不存在的 `/api/auth/refresh-activity`
2. auth.js 调用错误的 `/api/auth/status`
3. 响应字段判断错误 `data.authenticated` vs `data.logged_in`

### Suggested Fix
```javascript
// auth.js
function checkSession() {
    apiFetch('/api/auth/check-session', {
        credentials: 'same-origin',
        cache: 'no-store'
    })
        .then(response => response.json())
        .then(data => {
            if (data.logged_in === true) {
                // 已登录，显示用户名
            } else {
                window.location.href = '/login';
            }
        });
}
```

### Metadata
- Reproducible: yes
- Related Files:
  - cmd/logmonitor/src/static/js/auth.js
  - cmd/logmonitor/src/static/js/session.js
- See Also: LRN-20260411-001

---

## [ERR-20260412-001] dnd-bypass

**Logged**: 2026-04-12T00:10:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
PushCoordinator.push_raw() 方法绕过 DND 免打扰检查

### Error
免打扰时间段内仍然收到推送消息

### Context
- `push_raw()` 方法没有调用 `should_cache_now()` 检查
- `_push_aggregated()` 调用 `push_raw()` 绕过 DND 限制
- 聚合摘要在免打扰时段仍然会推送

### Suggested Fix
在 `push_raw()` 方法开头添加 DND 检查：
```python
def push_raw(self, content: str, logs: List[LogRecord], ...):
    if self.dnd_service.should_cache_now():
        self.dnd_service.cache_message(content)
        logger.debug(f"push_raw: 消息已缓存（免打扰时段）")
        return False
    # 原有推送逻辑...
```

### Metadata
- Reproducible: yes
- Related Files:
  - cmd/logmonitor/src/monitor_core/push_coordinator.py
- See Also: LRN-20260412-001

---

## [ERR-20260412-002] fnpack-json-format

**Logged**: 2026-04-12T00:15:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
fnpack.json 格式错误导致解析失败

### Error
```python
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 55 column 5 (char 1827)
```

### Context
- FnDepot 仓库的 fnpack.json
- `fnlogpush.history` 结束后缺少逗号
- `usbrsync.history` 有尾随逗号

### Suggested Fix
使用 Python 验证 JSON：
```bash
python3 -c "import json; json.load(open('fnpack.json'))"
```

### Metadata
- Reproducible: yes
- Related Files:
  - project/FnDepot/fnpack.json
- See Also: LRN-20260412-003

---
