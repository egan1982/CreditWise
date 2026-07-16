#!/bin/bash
# =============================================================================
# CreditWise 离线部署 — 准备脚本（在有外网的机器上执行）
#
# 核心思路：在外网机器上构建完整 Docker 镜像（含前端编译 + Python 依赖），
#           导出镜像 + 打包源码，生成一键离线部署包。
#           内网服务器只需 docker load + docker compose up，无需 build。
#
# 用法：
#   chmod +x scripts/prepare_offline.sh
#   ./scripts/prepare_offline.sh              # 标准模式（现有行为）
#   ./scripts/prepare_offline.sh --protected   # 受保护模式（Cython 编译 + 最小文件集打包）
#
# 产出：creditwise_offline_bundle.tar.gz（约 1.5GB）
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUNDLE_DIR="$PROJECT_ROOT/offline_bundle"

# === v1.5 新增：--protected 参数解析 ===
PROTECTED_MODE=false
if [ "$1" = "--protected" ]; then
    PROTECTED_MODE=true
fi

if [ "$PROTECTED_MODE" = "true" ]; then
    IMAGE_NAME="creditwise:protected"
    COMPOSE_FILE="docker-compose.compiled.yml"
else
    IMAGE_NAME="creditwise:latest"
    COMPOSE_FILE="docker-compose.yml"
fi

if [ "$PROTECTED_MODE" = "true" ]; then
    echo "============================================================"
    echo " CreditWise 离线部署 — 准备离线包 [受保护模式]"
    echo "============================================================"
else
    echo "============================================================"
    echo " CreditWise 离线部署 — 准备离线包"
    echo "============================================================"
fi
echo ""
echo "此脚本将在当前机器上构建完整 Docker 镜像，打包后传输到内网服务器。"
echo "预计耗时 5-15 分钟（取决于网络和机器性能）。"
echo ""

# =============================================================================
# 前置检查
# =============================================================================
if ! command -v docker &>/dev/null; then
    echo -e "${RED}Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo -e "${RED}Docker daemon 未运行，请先启动 Docker${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 可用: $(docker --version)${NC}"
echo ""

# 清理旧的 bundle
if [ -d "$BUNDLE_DIR" ]; then
    echo -e "${YELLOW}清理旧的 offline_bundle/ ...${NC}"
    rm -rf "$BUNDLE_DIR"
fi
mkdir -p "$BUNDLE_DIR/images"

# =============================================================================
# [1/4] 构建完整 Docker 镜像
# =============================================================================
echo -e "${GREEN}[1/4] 构建完整 Docker 镜像${NC}"
if [ "$PROTECTED_MODE" = "true" ]; then
    echo "  [受保护模式] 核心算法将在构建阶段编译为 .so，源码不进入镜像"
fi
echo "  包含：前端编译（Next.js + Vite + Tailwind）+ Python 依赖安装"
echo "  需要外网访问，首次构建约 5-10 分钟..."
echo ""

cd "$PROJECT_ROOT/docker"
docker compose -f "$COMPOSE_FILE" build

echo ""
echo -e "${GREEN}  ✅ Docker 镜像构建完成${NC}"
echo "  镜像: $IMAGE_NAME ($(docker image inspect $IMAGE_NAME --format='{{.Size}}' 2>/dev/null | awk '{printf "%.0fMB", $1/1024/1024}') )"
echo ""

# =============================================================================
# [2/4] 导出 Docker 镜像
# =============================================================================
echo -e "${GREEN}[2/4] 导出 Docker 镜像为 tar 文件${NC}"

IMAGE_TAR="$BUNDLE_DIR/images/creditwise-latest.tar"
echo "  导出 $IMAGE_NAME → $(basename "$IMAGE_TAR") ..."
docker save "$IMAGE_NAME" -o "$IMAGE_TAR"

IMAGE_SIZE=$(du -sh "$IMAGE_TAR" | cut -f1)
echo -e "${GREEN}  ✅ 镜像导出完成: ${IMAGE_SIZE}${NC}"
echo ""

# =============================================================================
# [3/4] 打包运行时文件（v1.5：受保护模式改为最小文件集，修正 Gap #2）
# =============================================================================
echo -e "${GREEN}[3/4] 打包运行时文件${NC}"

SOURCE_DIR="$BUNDLE_DIR/source"
mkdir -p "$SOURCE_DIR"

if [ "$PROTECTED_MODE" = "true" ]; then
    # v1.5 新增：受保护模式不 rsync 全量项目源码。
    # deploy_offline.sh 运行时完全不读取 source/ 下的 .py 文件——
    # 容器启动用的是镜像内 /app/，不是宿主机 source/。
    # 因此只需复制 deploy_offline.sh 实际依赖的最小文件集：
    # docker-compose.yml（重命名自 compiled 版）、scripts/、config/、.env 模板
    echo "  [受保护模式] 仅复制运行时必需文件（不含 .py 源码），从源头消除泄露面"
    mkdir -p "$SOURCE_DIR/docker" "$SOURCE_DIR/scripts" "$SOURCE_DIR/config"
    # deploy_offline.sh 执行不带 -f 的 docker compose up -d，按约定读取
    # 当前目录固定文件名 docker-compose.yml。将 compiled 版重命名为标准名，
    # 避免改动 deploy_offline.sh 本身（改动面更小、风险更低）
    cp "$PROJECT_ROOT/docker/$COMPOSE_FILE" "$SOURCE_DIR/docker/docker-compose.yml"
    cp -r "$PROJECT_ROOT/scripts/." "$SOURCE_DIR/scripts/"
    cp "$PROJECT_ROOT/config/users.yaml.example" "$SOURCE_DIR/config/" 2>/dev/null || true
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$SOURCE_DIR/.env"
    fi
else
    # 标准模式：保持原有全量 rsync 行为不变
    echo "  排除: .git, node_modules, workspace, logs, *.db 等运行时文件"

    # 使用 rsync 排除不需要的文件（macOS/Linux 均自带）
    rsync -a \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='.next' \
        --exclude='workspace' \
        --exclude='execution_states' \
        --exclude='task_results' \
        --exclude='logs' \
        --exclude='*.db' \
        --exclude='.env' \
        --exclude='offline_bundle' \
        --exclude='creditwise_offline_bundle*' \
        --exclude='.DS_Store' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='deepanalyze/SkyRL' \
        --exclude='deepanalyze/ms-swift' \
        --exclude='playground' \
        --exclude='graphiti-ui' \
        --exclude='.omo' \
        "$PROJECT_ROOT/" "$SOURCE_DIR/"

    # 从模板创建默认配置文件（如果不存在）
    if [ -f "$SOURCE_DIR/.env.example" ]; then
        cp "$SOURCE_DIR/.env.example" "$SOURCE_DIR/.env" 2>/dev/null || true
    fi
    if [ -f "$SOURCE_DIR/config/users.yaml.example" ]; then
        cp "$SOURCE_DIR/config/users.yaml.example" "$SOURCE_DIR/config/users.yaml" 2>/dev/null || true
    fi
fi

# 确保运行时需要的目录存在（两种模式都需要）
mkdir -p "$SOURCE_DIR"/{workspace,execution_states,task_results,logs,config}
# 预创建空的数据库文件（避免 Docker bind mount 将其创建为目录）
touch "$SOURCE_DIR/llm_manager.db" "$SOURCE_DIR/task_manager.db"

SOURCE_SIZE=$(du -sh "$SOURCE_DIR" | cut -f1)
echo -e "${GREEN}  ✅ 运行时文件打包完成: ${SOURCE_SIZE}${NC}"
if [ "$PROTECTED_MODE" = "true" ]; then
    echo "  （标准模式下 source/ 通常数十MB含全部源码；受保护模式应仅为数百KB级别，"
    echo "   若本次大小明显偏大，请检查是否误复制了源码目录）"
fi
echo ""

# =============================================================================
# [4/4] 生成离线包
# =============================================================================
echo -e "${GREEN}[4/4] 生成离线部署包${NC}"

BUNDLE_SIZE=$(du -sh "$BUNDLE_DIR" | cut -f1)
echo "  离线包内容大小: $BUNDLE_SIZE"

if [ "$PROTECTED_MODE" = "true" ]; then
    ARCHIVE_NAME="creditwise_offline_bundle_protected.tar.gz"
else
    ARCHIVE_NAME="creditwise_offline_bundle.tar.gz"
fi
cd "$PROJECT_ROOT"
tar -czf "$ARCHIVE_NAME" offline_bundle/

ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)

# 清理临时目录
rm -rf "$BUNDLE_DIR"

echo ""
echo "============================================================"
echo -e "${GREEN} 离线包准备完成！${NC}"
echo "============================================================"
echo ""
echo " 文件: $PROJECT_ROOT/$ARCHIVE_NAME"
echo " 大小: $ARCHIVE_SIZE"
echo ""
echo " 离线包内容:"
echo "   images/creditwise-latest.tar  — 完整 Docker 镜像（含前端+后端）"
echo "   source/                       — 项目源码 + 运行配置"
echo ""
echo " 下一步:"
echo "   1. 将 $ARCHIVE_NAME 传输到内网服务器（U盘/SCP）"
echo "   2. 在内网服务器上执行:"
echo "      tar -xzf $ARCHIVE_NAME"
echo "      cd offline_bundle/source"
echo "      chmod +x scripts/deploy_offline.sh"
echo "      ./scripts/deploy_offline.sh"
echo ""
echo "============================================================"
