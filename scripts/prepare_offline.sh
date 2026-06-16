#!/bin/bash
# =============================================================================
# CreditWise 离线部署 — 准备脚本（在有外网的机器上执行）
#
# 用法：
#   chmod +x scripts/prepare_offline.sh
#   ./scripts/prepare_offline.sh
#
# 产出：offline_bundle/ 目录，打包后传输到内网服务器
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUNDLE_DIR="$PROJECT_ROOT/offline_bundle"

echo "============================================================"
echo " CreditWise 离线部署 — 准备离线包"
echo "============================================================"
echo ""
echo "此脚本将在当前机器上下载所有依赖，打包后传输到内网服务器。"
echo ""

# 清理旧的 bundle
if [ -d "$BUNDLE_DIR" ]; then
    echo -e "${YELLOW}删除旧的 offline_bundle/ ...${NC}"
    rm -rf "$BUNDLE_DIR"
fi
mkdir -p "$BUNDLE_DIR"/{wheels,images,npm-cache,tailwind}

# =============================================================================
# [1/5] 下载 Docker 镜像
# =============================================================================
echo -e "${GREEN}[1/5] 拉取并导出 Docker 镜像${NC}"

IMAGES=("python:3.12-slim" "node:18-slim")
for img in "${IMAGES[@]}"; do
    echo "  拉取 $img ..."
    docker pull "$img"
    IMG_TAR="${img//:/-}.tar"  # python-3.12-slim.tar
    IMG_TAR="${IMG_TAR//\//-}"  # library-python-3.12-slim.tar (if needed)
    echo "  导出 $img → $BUNDLE_DIR/images/${IMG_TAR} ..."
    docker save "$img" -o "$BUNDLE_DIR/images/${IMG_TAR}"
done
echo -e "${GREEN}  ✅ Docker 镜像导出完成${NC}"

# =============================================================================
# [2/5] 下载 Python 依赖
# =============================================================================
echo -e "${GREEN}[2/5] 下载 Python 依赖 (pip download)${NC}"

REQ_FILE="$PROJECT_ROOT/requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
    echo -e "${RED}requirements.txt 不存在，请检查项目完整性${NC}"
    exit 1
fi

echo "  下载 Python wheels（使用 Docker Python 3.12 确保版本匹配）..."
# 用 Docker 内的 Python 3.12 下载 wheel，避免宿主 Python 版本与镜像不一致
docker run --rm -v "$PROJECT_ROOT":/app -w /app python:3.12-slim pip download -r requirements.txt -d "$BUNDLE_DIR/wheels"
WHEEL_COUNT=$(ls -1 "$BUNDLE_DIR/wheels"/*.whl 2>/dev/null | wc -l)
echo -e "${GREEN}  ✅ Python wheels: ${WHEEL_COUNT} 个文件${NC}"

# =============================================================================
# [3/5] 下载 Node.js 前端依赖
# =============================================================================
echo -e "${GREEN}[3/5] 下载 Node.js 依赖（npm pack）${NC}"

# demo/chat (Next.js 主前端)
CHAT_DIR="$PROJECT_ROOT/demo/chat"
if [ -f "$CHAT_DIR/package.json" ]; then
    echo "  下载 demo/chat 依赖..."
    cd "$CHAT_DIR"
    npm pack --pack-destination="$BUNDLE_DIR/npm-cache/chat" 2>/dev/null || {
        echo -e "${YELLOW}  ⚠️ npm pack 失败，将使用 npm install --package-lock-only 方案${NC}"
        npm install --package-lock-only 2>/dev/null || true
    }
    cd "$PROJECT_ROOT"
fi

# llm_manager_integrated/frontend (LLM Manager Vite 前端)
LLM_FRONTEND="$PROJECT_ROOT/llm_manager_integrated/frontend"
if [ -f "$LLM_FRONTEND/package.json" ]; then
    echo "  下载 llm_manager/frontend 依赖..."
    cd "$LLM_FRONTEND"
    npm pack --pack-destination="$BUNDLE_DIR/npm-cache/llm-frontend" 2>/dev/null || true
    cd "$PROJECT_ROOT"
fi

echo -e "${GREEN}  ✅ Node.js 依赖下载完成${NC}"

# =============================================================================
# [4/5] 编译 Tailwind CSS 静态文件
# =============================================================================
echo -e "${GREEN}[4/5] 编译 LLM Manager 前端（Vite JS + Tailwind CSS）${NC}"

LLM_FRONTEND_DIR="$PROJECT_ROOT/llm_manager_integrated/frontend"
LLM_STATIC_DIR="$PROJECT_ROOT/llm_manager_integrated/static"

if [ -f "$LLM_FRONTEND_DIR/package.json" ]; then
    cd "$LLM_FRONTEND_DIR"
    echo "  安装 npm 依赖..."
    npm install --production=false 2>/dev/null || {
        echo -e "${RED}npm install 失败，请确保 Node.js >= 18 已安装${NC}"
        exit 1
    }
    echo "  Vite 构建..."
    npm run build
    echo "  Tailwind CSS 编译..."
    npx tailwindcss -i ./styles/main.css -o "$LLM_STATIC_DIR/assets/main.css" --minify \
        --content "$LLM_STATIC_DIR/assets/**/*.html" \
        --content ./scripts/**/*.js \
        2>&1 | tail -1
    # 替换 CDN → 本地 CSS
    sed -i 's|<script src="https://cdn.tailwindcss.com.*></script>|<link rel="stylesheet" href="/llm-manager/assets/main.css">|' "$LLM_STATIC_DIR/assets/index.html"
    sed -i 's|https://cdn.tailwindcss.com;||g' "$LLM_STATIC_DIR/assets/index.html"
    cd "$PROJECT_ROOT"
fi

# 保存编译产物到离线包
mkdir -p "$BUNDLE_DIR/llm-manager-static/assets"
cp -r "$LLM_STATIC_DIR/assets"/* "$BUNDLE_DIR/llm-manager-static/assets/" 2>/dev/null || true
echo -e "${GREEN}  ✅ LLM Manager 前端编译完成（离线可用）${NC}"

# =============================================================================
# [5/5] 打包
# =============================================================================
echo -e "${GREEN}[5/5] 打包离线部署包${NC}"

BUNDLE_SIZE=$(du -sh "$BUNDLE_DIR" | cut -f1)
echo "  离线包大小: $BUNDLE_SIZE"

ARCHIVE_NAME="creditwise_offline_bundle.tar.gz"
cd "$PROJECT_ROOT"
tar -czf "$ARCHIVE_NAME" -C "$PROJECT_ROOT" offline_bundle/
ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)

echo ""
echo "============================================================"
echo -e "${GREEN} 离线包准备完成！${NC}"
echo "============================================================"
echo ""
echo " 文件: $PROJECT_ROOT/$ARCHIVE_NAME"
echo " 大小: $ARCHIVE_SIZE"
echo ""
echo " 下一步:"
echo "   1. 将 $ARCHIVE_NAME 传输到内网服务器"
echo "   2. 在目标服务器上执行: tar -xzf $ARCHIVE_NAME"
echo "   3. 然后执行: ./scripts/deploy_offline.sh"
echo ""
echo "============================================================"
