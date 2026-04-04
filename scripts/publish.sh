#!/bin/bash
# FNLogPush 发布脚本
# 执行完整发布流程：更新代码仓库

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  FNLogPush 发布脚本"
echo "=========================================="

# 获取版本号
VERSION=$(grep "^version" "$PROJECT_DIR/manifest" | awk -F'= ' '{print $2}')
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "当前版本: $VERSION"
echo "当前分支: $BRANCH"

# 1. 更新 GitHub
echo ""
echo "[1/2] 更新 GitHub 仓库..."
cd "$PROJECT_DIR"
if [ -d ".git" ]; then
    git add -A
    git commit -m "Release v$VERSION"
    git push origin "$BRANCH"
    echo "✓ GitHub 更新完成"
else
    echo "⚠ 未找到 Git 仓库，跳过"
fi

# 2. 更新 Gitee
echo ""
echo "[2/2] 更新 Gitee 仓库..."
cd "$PROJECT_DIR"
if git remote get-url gitee &>/dev/null; then
    git push gitee "$BRANCH"
    echo "✓ Gitee 更新完成"
else
    echo "⚠ 未配置 Gitee remote，跳过"
fi

echo ""
echo "=========================================="
echo "  发布完成！"
echo "=========================================="
