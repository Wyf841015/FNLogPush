# Errors Log

记录命令失败、异常和外部工具错误。

---

## [ERR-20260404-001] MeoW API HTTP 500

**Logged**: 2026-04-04T10:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
MeoW API 使用 GET 方式请求返回 500 错误

### Error
```
MeoW推送响应: {'status': 500, 'data': None, 'msg': '服务器内部错误'}
```

### Context
- 推送渠道：MeoW
- 请求方式：GET URL 编码
- 环境：飞牛NAS

### Suggested Fix
改用 POST JSON 方式：
```python
response = requests.post(url, json={'title': title, 'msg': msg})
```

### Metadata
- Reproducible: yes
- Related Files: push_service.py

---

## [ERR-20260404-002] GitHub TLS Connection

**Logged**: 2026-04-04T10:20:00+08:00
**Priority**: medium
**Status**: workaround
**Area**: infra

### Summary
GitHub 连接频繁出现 TLS 错误

### Error
```
fatal: unable to access 'https://github.com/...': GnuTLS recv error (-110): The TLS connection was non-properly terminated.
fatal: Failed to connect to github.com port 443 after 134xxx ms: Couldn't connect to server
```

### Context
- 网络环境可能存在问题
- 多次重试后有时成功

### Suggested Fix
- 多次重试
- 检查网络连接
- 等待网络恢复

### Metadata
- Reproducible: intermittent
- Related Files: N/A

---

## [ERR-20260404-003] GitHub Authentication

**Logged**: 2026-04-04T09:50:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
GitHub token 过期导致推送失败

### Error
```
fatal: Authentication failed for 'https://github.com/...'
remote: Invalid username or token. Password authentication is not supported for Git operations.
```

### Context
- token: <旧token> (已过期)
- 新 token: <新token>

### Suggested Fix
```bash
git remote set-url origin https://ghp_NEW_TOKEN@github.com/repo.git
```

### Metadata
- Reproducible: no (token 已更新)
- Related Files: N/A

---
