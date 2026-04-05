# FNLogPush 飞牛NAS日志哨兵

> 自动监控飞牛NAS系统日志和备份进度，实时推送至多种渠道

[![Platform](https://img.shields.io/badge/platform-FNOS-blue)](https://www.fnnas.com/)
[![Version](https://img.shields.io/badge/version-0.7.5-green)](https://gitee.com/wyf1015/FNLogPush)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

## 功能特性

### 📊 日志监控
- 实时监控飞牛NAS系统日志
- 关键字过滤和告警匹配
- 支持多种日志类型

### 💾 备份监控
- 监控备份任务进度
- 备份完成通知
- 备份历史记录

### 📢 多渠道推送
- 企业微信机器人
- 钉钉机器人
- 飞书机器人
- Bark推送
- PushPlus推送
- MeoW推送
- Webhook自定义

### 🔔 告警聚合
- 智能告警聚合
- 重复告警合并
- 免打扰模式

### 🎨 界面特性
- 6个精选主题（暗夜紫/深色/深海蓝/清新绿/暮色橙/科技感霓虹）
- 响应式设计
- 实时WebSocket推送
- 移动端优化
- 加载动画、骨架屏、卡片悬浮动效

## 安装方式

1. 在飞牛NAS应用中心下载安装
2. 或访问 [Gitee发布页](https://gitee.com/wyf1015/FNLogPush/releases) 下载FPK

## 配置说明

### 推送渠道配置

支持以下推送渠道，请在Web界面配置：

| 渠道 | 配置项 |
|------|--------|
| 企业微信 | Webhook地址 |
| 钉钉 | Webhook地址 |
| 飞书 | Webhook地址 |
| Bark | 设备Key |
| Webhook | 自定义URL |

### 关键字监控

配置需要监控的日志关键字，支持正则表达式匹配。

## 技术栈

- **后端**: Python 3.12 + Flask + Flask-SocketIO
- **前端**: Bootstrap 5 + Font Awesome
- **数据库**: SQLite
- **部署**: FPK安装包

## 目录结构

```
FNLogPush/
├── app/                    # 应用配置
│   ├── config/            # 权限配置
│   └── ui/                # UI配置
├── cmd/                   # 命令脚本
│   └── logmonitor/        # 主程序
│       └── src/           # 源代码
│           ├── routes/    # 路由
│           ├── models/    # 数据模型
│           ├── monitor_core/ # 监控核心
│           └── static/    # 静态资源
├── config/                # 配置文件
├── ui/                    # UI资源
└── manifest              # FPK清单
```

## 界面预览

- **仪表盘**: KPI卡片展示推送统计
- **推送配置**: 多渠道Webhook配置
- **日志监控**: 关键字过滤和实时日志
- **备份监控**: 备份任务进度跟踪
- **历史记录**: 推送历史查询

## 注意事项

- 需要Python 3.12环境
- 默认端口: 19800
- 数据存储在应用目录内

## 更新日志

### v0.7.5 (2026-04-05)
- 🛠️ **代码质量优化** - 提取公共函数，减少重复代码
- 🛠️ **代码质量优化** - 新增 constants.py 常量模块
- 🛠️ **代码质量优化** - 状态值使用常量替代硬编码字符串
- 🛠️ **代码质量优化** - Session/重试间隔等数值使用常量管理

### v0.7.4 (2026-04-05)
- 🔒 **安全加固：移除硬编码 Secret Key** - 使用环境变量或配置文件固定密钥
- 🔒 **安全加固：Webhook 改用 POST 请求** - 默认使用 POST JSON body，更安全
- 🔒 **安全加固：敏感信息加密存储** - Webhook URL、Token 等敏感字段自动加密
- 🔧 新增 `utils/crypto.py` 加密模块（Fernet AES 加密）
- 🔧 新增 `.encrypt_key` 密钥文件管理

### v0.7.3 (2026-04-05)
- ⚡ **性能优化：WebSocket推送健康状态** - 替代轮询，实时推送系统状态，降低服务器负载
- 🔧 后台线程定期推送健康数据到 WebSocket
- 🔧 前端 WebSocket 监听 health_status 事件
- 🔧 保留轮询作为 WebSocket 断开时的备用方案

### v0.7.2 (2026-04-05)
- 🎨 **界面全面升级**：字体系统、动画效果、状态指示器
- 📊 添加页面加载进度条 + 骨架屏加载
- 🎬 卡片入场动画 (fadeInUp + stagger)
- 💫 按钮点击波纹 + 悬浮上浮效果
- 📦 卡片悬浮动效 (translateY + shadow)
- ✨ 输入框聚焦/悬浮效果
- 📱 模态框缩放动画
- 🔔 Toast 通知滑动动画
- 🎯 状态指示器脉冲发光
- 🎨 自定义滚动条样式
- ♿ prefers-reduced-motion 无障碍支持
- 🎨 **主题系统重构**：分离独立主题CSS文件
- ✨ 新增科技感霓虹主题（Cyber）

### v0.7.0 (2026-04-05)
- 🔒 **新增Session超时机制**：5分钟无操作自动退出登录

### v0.6.9 (2026-03-29)
- 🆕 新增 MeoW 推送渠道

### v0.6.8 (2026-03-29)
- 🆕 新增存储管理事件、防火墙事件

### v0.6.7 (2026-03-28)
- 🔧 Web界面优化、JS模块化拆分

### v0.6.6
- ✨ **WebSocket实时推送** - 启用前后端WebSocket通信，新日志实时推送到前端
- ✨ **Schema验证** - 新增配置Schema验证，统一配置中心
- 🔧 **删除冗余文件** - 移除history_service1.py, mappings1.py, base1.py
- 🔧 **修复重复推送** - 优化推送逻辑，仅在所有渠道失败时加入重试队列
- 🔧 **推送历史详情** - 详情弹窗显示每个渠道的推送结果

### v0.6.0
- ✨ 新增钉钉推送渠道 - 支持Webhook + 签名验证
- ✨ 新增飞书推送渠道 - 支持Webhook
- ✨ 新增Bark推送渠道 - iOS设备推送
- ✨ 新增PushPlus推送渠道 - 支持Token + 群组
- 🔧 修复推送历史记录准确性问题 - 同步执行推送并返回实际结果
- 🔧 彻底解决登录session问题 - 统一credentials配置，定时检查session有效性
- 🔧 修复退出登录后无法重新登录的问题

### v0.5.0
- 初始版本
- 日志监控功能
- 多渠道推送支持
- 备份进度监控
- Web界面管理

## 许可证

MIT License

## 作者

- 作者: 再见一零一二
- Gitee: https://gitee.com/wyf1015
- Email: 64652178@qq.com

## 赞助

如果这个项目对你有帮助，欢迎赞助支持！

---
*让日志监控变得更简单*
