# Learnings Log

## [LRN-20260403-001] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: frontend

### Summary
新增事件时需要同时修改前端和后端，并预添加到默认配置避免"新事件"提示

### Details
在 FNLogPush 项目中新增 CreateStorage、FW_ENABLE、MountStorage 等事件时：
1. 前端 `main.js` - 在 `eventCategories` 中添加事件定义
2. 后端 `mappings.py` - 在 `EVENT_NAME_MAP` 中添加名称映射
3. 默认配置 `manager.py` - 在 `DEFAULT_CONFIG.event_ids` 中预添加
4. 配置加载 `manager.py` - 修改 `load_config()` 合并用户已有事件和新事件

### Suggested Action
建立事件添加检查清单，确保前后端同步

### Metadata
- Source: conversation
- Related Files: 
  - cmd/logmonitor/src/static/js/main.js
  - cmd/logmonitor/src/config/mappings.py
  - cmd/logmonitor/src/config/manager.py
- Tags: events, sync, frontend, backend

---

## [LRN-20260403-002] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: config

### Summary
用户旧配置会覆盖 DEFAULT_CONFIG，需要合并列表类型配置

### Details
在 `load_config()` 中使用 `merged_config.update(config)` 时：
- 用户的 `event_ids: []` 会覆盖默认的 `event_ids: ['CreateStorage', ...]`
- 导致新事件仍显示为"新事件"

解决方案：
```python
if 'event_ids' in config and isinstance(config['event_ids'], list):
    default_ids = set(self.DEFAULT_CONFIG.get('event_ids', []))
    user_ids = set(config['event_ids'])
    merged_config['event_ids'] = list(user_ids | default_ids)
```

### Metadata
- Source: error
- Pattern-Key: config.merge_lists
- Related Files: cmd/logmonitor/src/config/manager.py
- Tags: config, merge, backward_compatibility

---

## [LRN-20260403-003] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
GitHub 新建仓库默认分支是 main，不是 master

### Details
推送代码时报错：
```
! [rejected] master -> master (fetch first)
```
检查后发现仓库默认分支是 `main`。

解决：
```bash
git push origin master:main  # 推送到 main 分支
```

### Metadata
- Source: error
- Pattern-Key: git.push.default_branch
- Tags: git, github

---

## [LRN-20260403-004] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
Windows 文件的 BOM 字符会导致 API Token 认证失败

### Details
Gitee Token 认证失败：
```
Incorrect username or password (access token)
```
检查发现 token 文件有 BOM 字符 `\xEF\xBB\xBF`。

解决：
```python
with open('token.txt', 'r', encoding='utf-8-sig') as f:  # utf-8-sig 自动去除 BOM
    token = f.read().strip()
```

### Metadata
- Source: error
- Pattern-Key: file.bom_encoding
- Tags: encoding, api, authentication

---

## [LRN-20260403-005] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: frontend

### Summary
页面初始化时使用 Promise.all 同步多个 API 请求，避免状态显示先后不一

### Details
页面刷新时，日志数据库和备份数据库状态显示有先后差异。

解决：
```javascript
Promise.all([
    loadStatus(),
    loadConfig(),
    checkDatabase()
]).then(() => {
    loadHistory();
});
```

### Metadata
- Source: conversation
- Pattern-Key: ui.sync_init
- Tags: async, initialization, ux

---

## [LRN-20260403-006] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: frontend

### Summary
main.js 自动拆分失败，需要更细致的依赖分析和手动拆分

### Details
尝试将 main.js (2648行) 自动拆分为多个模块：
- dashboard.js, history.js, config.js, monitor.js, database.js
- 因函数间依赖复杂，拆分后出现语法错误

结论：
1. 单文件结构在当前规模仍可接受
2. 如需拆分，应分阶段手动进行
3. 或在开发新功能时同步拆分

### Metadata
- Source: error
- Pattern-Key: js.module_split
- Related Files: cmd/logmonitor/src/static/js/main.js
- Tags: refactoring, modules

---

## [LRN-20260403-007] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: docs

### Summary
版本更新流程：manifest → readme.md → fnpack.json → FnDepot/readme.md

### Details
用户明确要求的版本更新步骤：
1. 更新 `project/log-monitor-fpk/manifest` 中的版本号
2. 将更新内容写入 `project/log-monitor-fpk/readme.md`
3. 更新 `project/FnDepot/fnpack.json` 中的版本号和更新内容
4. 将更新内容写入 `project/FnDepot/fnlogpush/readme.md`

### Metadata
- Source: user_feedback
- Pattern-Key: release.version_update
- Tags: version, release, workflow

---

## [LRN-20260403-008] best_practice

**Logged**: 2026-04-03T18:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: backend

### Summary
代码优化建议：SELECT * 应替换为明确列名

### Details
在代码分析中发现多处使用 `SELECT *`：
```python
cursor.execute("SELECT * FROM operations")
```

应改为：
```python
cursor.execute("SELECT id, status, created_at FROM operations WHERE ...")
```

理由：
- 减少 I/O 和内存占用
- 可利用索引覆盖查询
- 避免不必要的数据传输

### Metadata
- Source: analysis
- Pattern-Key: sql.select_star
- Tags: database, performance, optimization

---
