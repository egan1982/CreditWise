#!/bin/bash
# =============================================================================
# CreditWise 离线部署脚本（在内网服务器上执行）
#
# 前置条件：
#   1. 已将 offline_bundle.tar.gz 传输到此服务器并解压
#   2. 已安装 Docker（如未安装，请手动安装：apt-get install docker.io docker-compose）
#   3. Dockerfile 中已添加离线 pip install 逻辑（FROM 基础镜像后优先从 wheels 目录安装）
#
# 用法：
#   chmod +x scripts/deploy_offline.sh
#   ./scripts/deploy_offline.sh
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
echo " CreditWise 离线部署"
echo "============================================================"
echo ""

# 检查离线包是否存在
if [ ! -d "$BUNDLE_DIR" ]; then
    echo -e "${RED}离线包 offline_bundle/ 不存在！请先传输并解压离线包。${NC}"
    echo "准备离线包：在可访问外网的机器上执行 scripts/prepare_offline.sh"
    exit 1
fi

# =============================================================================
# [0] 部署模式选择
# =============================================================================
echo -e "${GREEN}[0] 选择部署模式${NC}"
echo ""
echo "  [1] 单用户模式 — 无需登录认证"
echo "  [2] 内网多用户 — Basic Auth 认证"
echo ""
read -p "请选择 [1/2] (默认: 1): " DEPLOY_MODE
DEPLOY_MODE=${DEPLOY_MODE:-1}

if [ "$DEPLOY_MODE" = "2" ]; then
    ENABLE_AUTH=true
    MODE_LABEL="内网多用户模式"
else
    ENABLE_AUTH=false
    MODE_LABEL="单用户模式"
fi
echo -e "${GREEN}已选择: ${MODE_LABEL}${NC}"
echo ""

# =============================================================================
# [1] 加载 Docker 镜像
# =============================================================================
echo -e "${GREEN}[1] 加载 Docker 镜像${NC}"
IMAGES_DIR="$BUNDLE_DIR/images"
if [ -d "$IMAGES_DIR" ]; then
    for img_tar in "$IMAGES_DIR"/*.tar; do
        [ -f "$img_tar" ] || continue
        echo "  加载 $(basename "$img_tar") ..."
        docker load -i "$img_tar"
    done
    echo -e "${GREEN}  ✅ Docker 镜像加载完成${NC}"
else
    echo -e "${YELLOW}  ⚠️ images/ 目录不存在，跳过镜像加载${NC}"
    echo "  将尝试在线构建（需要外网访问）"
fi

# =============================================================================
# [2] 检查基础环境
# =============================================================================
echo -e "${GREEN}[2] 检查基础环境${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker 未安装，请手动安装后重试${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Docker: $(docker --version)${NC}"

# 端口检查
for PORT in 8200 8100; do
    PORT_CHECK=$(ss -tlnp 2>/dev/null | grep ":${PORT} " || true)
    if [ -n "$PORT_CHECK" ]; then
        echo -e "${RED}✗ 端口 ${PORT} 已被占用${NC}"
        exit 1
    fi
done
echo -e "${GREEN}  ✓ 端口 8200, 8100 可用${NC}"

# 磁盘
DISK_AVAIL=$(df -BM "$PROJECT_ROOT" | tail -1 | awk '{print $4}' | sed 's/M//')
if [ "$DISK_AVAIL" -lt 2048 ]; then
    echo -e "${RED}✗ 磁盘空间不足 2GB（当前 ${DISK_AVAIL}MB）${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ 磁盘可用: ${DISK_AVAIL}MB${NC}"

# =============================================================================
# [3] 配置环境
# =============================================================================
echo -e "${GREEN}[3] 配置环境${NC}"

ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
    else
        touch "$ENV_FILE"
    fi
fi

# ENABLE_AUTH
if grep -q '^ENABLE_AUTH=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^ENABLE_AUTH=.*|ENABLE_AUTH=${ENABLE_AUTH}|" "$ENV_FILE"
else
    echo "ENABLE_AUTH=${ENABLE_AUTH}" >> "$ENV_FILE"
fi

# 加密密钥
if ! grep -q '^LLM_MANAGER_ENCRYPTION_KEY=.\+' "$ENV_FILE" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  LLM_MANAGER_ENCRYPTION_KEY 未设置，请在首次构建后生成${NC}"
fi

# 多用户配置
if [ "$ENABLE_AUTH" = "true" ]; then
    CONFIG_FILE="$PROJECT_ROOT/config/users.yaml"
    if [ ! -f "$CONFIG_FILE" ]; then
        cp "$PROJECT_ROOT/config/users.yaml.example" "$CONFIG_FILE"
        echo -e "${YELLOW}⚠️  请编辑 config/users.yaml 配置用户账号${NC}"
    fi
fi

# 预创建数据库文件
for DB_FILE in llm_manager.db task_manager.db; do
    DB_PATH="$PROJECT_ROOT/$DB_FILE"
    [ -f "$DB_PATH" ] || touch "$DB_PATH"
done

# =============================================================================
# [4] 构建并启动
# =============================================================================

# 恢复 LLM Manager 编译产物
LLM_STATIC="$PROJECT_ROOT/llm_manager_integrated/static/assets"
if [ -d "$BUNDLE_DIR/llm-manager-static/assets" ]; then
    echo -e "${GREEN}  恢复 LLM Manager 编译前端...${NC}"
    cp -r "$BUNDLE_DIR/llm-manager-static/assets"/* "$LLM_STATIC/" 2>/dev/null || true
fi

echo -e "${GREEN}[4] 构建 Docker 镜像${NC}"
cd "$PROJECT_ROOT/docker"

# 离线模式：将 wheels 复制到 Docker 构建上下文
if [ -d "$BUNDLE_DIR/wheels" ] && ls "$BUNDLE_DIR/wheels"/*.whl >/dev/null 2>&1; then
    echo "  离线模式: 复制 wheels 到构建上下文..."
    rm -rf .offline_wheels/*.whl 2>/dev/null
    cp "$BUNDLE_DIR/wheels"/*.whl .offline_wheels/ 2>/dev/null || true
    echo "  已复制 $(ls -1 .offline_wheels/*.whl 2>/dev/null | wc -l) 个 wheel 文件"
fi

echo "构建中..."
ENABLE_AUTH=${ENABLE_AUTH} OFFLINE_MODE=true docker compose build

echo ""
echo -e "${GREEN}[5] 启动服务${NC}"
ENABLE_AUTH=${ENABLE_AUTH} docker compose up -d

echo ""
echo "等待服务启动..."
sleep 5
for i in $(seq 1 6); do
    if curl -sf http://localhost:8200/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务启动成功！${NC}"
        break
    fi
    [ $i -eq 6 ] && echo -e "${RED}⚠️  服务可能未完全启动${NC}"
    sleep 5
done

SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "============================================================"
echo -e "${GREEN} 部署完成！${NC}"
echo "============================================================"
echo ""
echo " 访问地址: http://${SERVER_IP}:8200"
echo " 部署模式: ${MODE_LABEL}"
echo ""
