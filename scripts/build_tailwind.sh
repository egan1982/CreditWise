#!/bin/bash
# =============================================================================
# Tailwind CSS 本地编译脚本
#
# 将 LLM Manager 管理页面的 Tailwind CDN 替换为本地静态 CSS
# 用法：./scripts/build_tailwind.sh
#
# 前置条件：Node.js ≥ 16、npm 已安装
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STATIC_DIR="$PROJECT_ROOT/llm_manager_integrated/static"

cd "$PROJECT_ROOT"

echo "=== 编译 Tailwind CSS 静态文件 ==="

# 临时安装 Tailwind CLI
if ! npx tailwindcss --help &>/dev/null 2>&1; then
    echo "安装 tailwindcss CLI..."
    npm install tailwindcss@3.4.0 --no-save
fi

# 生成 CSS：扫描 static/ 下所有 HTML，提取用到的 class
echo "扫描 HTML 并生成 CSS..."
npx tailwindcss \
    -i /dev/stdin \
    -o "$STATIC_DIR/tailwind.css" \
    --minify \
    --content "$STATIC_DIR/**/*.html" <<EOF
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

echo "✅ tailwind.css 已生成到 $STATIC_DIR/tailwind.css"
