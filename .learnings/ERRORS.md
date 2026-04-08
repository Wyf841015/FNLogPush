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
