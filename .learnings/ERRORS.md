# Errors Log

## [ERR-20260406-001] git-rebase

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
Git rebase 二进制文件产生冲突

### Error
```
Cannot merge binary files: ICON.PNG (HEAD vs. 1618808 (更新应用图标 (v0.7.6)))
CONFLICT (content): Merge conflict in ICON.PNG
```

### Context
- 操作：`git pull gitee master --rebase`
- 原因：远程和本地都有对二进制文件的修改
- 二进制文件：ICON.PNG, ICON_128.PNG, ICON_256.PNG 等

### Suggested Fix
1. 使用 `git rebase --abort` 放弃 rebase
2. 直接 `git push --force` 推送本地版本
3. 或在修改二进制文件前先 pull 远程最新版本

### Metadata
- Reproducible: yes
- Related Files: ICON*.PNG
- See Also: LRN-20260406-004

---

## [ERR-20260406-002] GitHub Connection

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
GitHub 连接超时，无法推送

### Error
```
fatal: unable to access 'https://github.com/...': GnuTLS recv error (-110): The TLS connection was non-properly terminated.
fatal: Failed to connect to github.com port 443 after 134409 ms: Couldn't connect to server
```

### Context
- 操作：`git push origin master`
- 目标：GitHub
- 多次重试均失败

### Suggested Fix
1. 检查网络代理设置
2. 稍后重试
3. 使用 Gitee 作为替代

### Metadata
- Reproducible: intermittent
- Related Files: FNLogPush, FnDepot
- See Also: LRN-20260406-004

---

## [ERR-20260406-003] SkillHub Path

**Logged**: 2026-04-06T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
SkillHub CLI 安装后命令找不到

### Error
```
/bin/sh: 1: skillhub: not found
```

### Context
- 操作：`skillhub install seede-design`
- 原因：CLI 安装到 `/root/.local/bin` 但不在 PATH 中

### Suggested Fix
```bash
export PATH="$PATH:/root/.local/bin"
skillhub install seede-design
```

### Metadata
- Reproducible: yes
- See Also: LRN-20260406-005

---
