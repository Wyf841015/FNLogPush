# Learnings Log

记录开发过程中的经验、教训和最佳实践。

---

## [LRN-20260404-001] best_practice

**Logged**: 2026-04-04T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
添加新推送渠道时，必须同时更新 push_channels 配置和具体渠道配置

### Details
在添加 MeoW 推送渠道时，只添加了 meow 配置项，但没有将其添加到 push_channels 字典中。导致 push_service.push_message() 调用时，meow 渠道不会被执行。

### Suggested Action
添加新渠道时，确保：
1. 在 main.js 的 push_channels 中添加 `meow: checkbox.checked`
2. 在 base.py 的配置更新检查中添加 `'meow'` 到检测列表
3. 在 push_service.py 的 configure_from_config 中添加渠道配置加载

### Metadata
- Source: error
- Related Files: main.js, base.py, push_service.py
- Pattern-Key: push-channel.config-sync

---

## [LRN-20260404-002] best_practice

**Logged**: 2026-04-04T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
MeoW API 使用 POST JSON 方式更可靠

### Details
API 文档声称支持 GET/POST，但实际测试发现：
- GET 方式在某些环境返回 500 错误
- POST JSON 方式 `{"title": "...", "msg": "..."}` 稳定可靠

### Suggested Action
优先使用 POST JSON 方式：
```python
response = requests.post(url, json={'title': title, 'msg': msg})
```

### Metadata
- Source: error
- Related Files: push_service.py

---

## [LRN-20260404-003] knowledge_gap

**Logged**: 2026-04-04T00:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: backend

### Summary
自定义标题模板时，消息内容处理逻辑需要调整

### Details
当用户设置自定义标题时，消息内容应该是完整的原始内容，而不是跳过第一行。使用配置的标题后，整个消息作为内容推送。

### Suggested Action
```python
if self.title:
    title = self.title[:50]
    msg = content  # 整个消息作为内容
else:
    title = lines[0][:50]
    msg = lines[1] if len(lines) > 1 else ""
```

### Metadata
- Source: user_feedback
- Related Files: push_service.py

---

## [LRN-20260404-004] best_practice

**Logged**: 2026-04-04T00:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra

### Summary
GitHub/Gitee 推送时需要正确配置 token 和分支

### Details
- token 过期需要更新远程 URL
- 仓库可能使用 main 分支而非 master
- 推送到不同分支使用 `git push origin source:target`

### Suggested Action
```bash
# 更新 token
git remote set-url origin https://ghp_TOKEN@github.com/repo.git

# 推送到 main 分支
git push origin master:main
```

### Metadata
- Source: error

---

## [LRN-20260404-005] best_practice

**Logged**: 2026-04-04T00:00:00+08:00
**Priority**: low
**Status**: pending
**Area**: config

### Summary
飞牛NAS FPK 打包时，需要检查 .gitignore 确保不包含调试文件

### Details
打包后发现 __pycache__、.learnings 等目录被包含在包中

### Suggested Action
确保 .gitignore 包含：
```
__pycache__/
*.pyc
*.pyo
.learnings/
```

### Metadata
- Source: error
- Related Files: manifest, .gitignore

---
