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

**Logged**: 2026-04-08T23:22:00+08:00
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
