#!/bin/bash
#
# BMAD-Kimi 安装脚本
#

set -e

echo "🚀 安装 BMAD-Kimi..."
echo "==================="
echo ""

# 检查依赖
echo "📋 检查依赖..."

# 检查OpenClaw
if ! command -v openclaw &> /dev/null; then
    echo "❌ 错误: 未安装 OpenClaw"
    echo "请先安装 OpenClaw: https://github.com/openclaw/openclaw"
    exit 1
fi
echo "✅ OpenClaw 已安装"

# 检查Kimi API Key
if [ -z "$KIMI_API_KEY" ]; then
    echo "⚠️  警告: 未设置 KIMI_API_KEY 环境变量"
    echo "请在安装后设置: export KIMI_API_KEY='your-api-key'"
fi

# 创建安装目录
INSTALL_DIR="/usr/local/bin"
if [ ! -w "$INSTALL_DIR" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
fi

echo ""
echo "📦 安装文件..."

# 复制主脚本
cp "$(dirname "$0")/bk" "$INSTALL_DIR/bk"
chmod +x "$INSTALL_DIR/bk"

# 检查PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "⚠️  请将 $INSTALL_DIR 添加到 PATH:"
    echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
fi

echo ""
echo "✅ BMAD-Kimi 安装完成!"
echo ""
echo "使用方法:"
echo "  bk --help          显示帮助"
echo "  bk version         显示版本"
echo "  bk full ./project  执行完整流程"
echo ""
echo "请确保已设置 KIMI_API_KEY 环境变量"
