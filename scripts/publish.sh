#!/bin/bash
# FNLogPush 发布脚本
# 执行完整发布流程：更新代码仓库 + 同步 FnDepot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FNDEPOT_DIR="$PROJECT_DIR/../FnDepot"

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
echo "[1/4] 更新 GitHub 仓库..."
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
echo "[2/4] 更新 Gitee 仓库..."
cd "$PROJECT_DIR"
if git remote get-url gitee &>/dev/null; then
    git push gitee "$BRANCH"
    echo "✓ Gitee 更新完成"
else
    echo "⚠ 未配置 Gitee remote，跳过"
fi

# 3. 复制打包文件到 FnDepot
echo ""
echo "[3/4] 复制打包文件到 FnDepot..."
if [ -f "$PROJECT_DIR/fnlogpush.fpk" ]; then
    mkdir -p "$FNDEPOT_DIR/fnlogpush"
    cp "$PROJECT_DIR/fnlogpush.fpk" "$FNDEPOT_DIR/fnlogpush/"
    echo "✓ 打包文件已复制"
else
    echo "⚠ 未找到 fnlogpush.fpk，请先打包"
fi

# 复制 README
if [ -f "$PROJECT_DIR/readme.md" ]; then
    cp "$PROJECT_DIR/readme.md" "$FNDEPOT_DIR/fnlogpush/"
fi

# 4. 推送 FnDepot 到 GitHub
echo ""
echo "[4/4] 推送 FnDepot 到 GitHub..."
cd "$FNDEPOT_DIR"
if [ -d ".git" ]; then
    git add -A
    git commit -m "Update FNLogPush v$VERSION"
    git push origin main
    echo "✓ FnDepot 推送完成"
else
    echo "⚠ 未找到 FnDepot Git 仓库，跳过"
fi

echo ""
echo "=========================================="
echo "  发布完成！"
echo "=========================================="
