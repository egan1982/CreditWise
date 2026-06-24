#!/bin/bash
# =============================================================================
# CreditWise 离线部署脚本（在内网服务器上执行）
#
# 前置条件：
#   1. 已将 creditwise_offline_bundle.tar.gz 传输到此服务器并解压
#   2. 已安装 Docker 20.10+ 和 Docker Compose 2.0+
#
# 用法：
#   tar -xzf creditwise_offline_bundle.tar.gz
#   cd offline_bundle/source
#   chmod +x scripts/deploy_offline.sh
#   ./scripts/deploy_offline.sh
#
# 注意：此脚本不会执行 docker build，直接使用预构建的镜像。
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 离线包结构：offline_bundle/images/*.tar + offline_bundle/source/
# 此脚本位于 offline_bundle/source/scripts/，镜像在 offline_bundle/images/
BUNDLE_DIR="$(dirname "$PROJECT_ROOT")"

echo "============================================================"
echo " CreditWise 离线部署"
echo "============================================================"
echo ""

# =============================================================================
# 前置检查
# =============================================================================
if ! command -v docker &>/dev/null; then
    echo -e "${RED}Docker 未安装${NC}"
    echo ""
    echo "请先安装 Docker："
    echo "  Ubuntu/Debian: sudo apt-get install -y docker.io docker-compose-plugin"
    echo "  CentOS/RHEL:   sudo yum install -y docker docker-compose-plugin"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo -e "${RED}Docker daemon 未运行${NC}"
    echo "  启动: sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}✓ Docker: $(docker --version)${NC}"

# =============================================================================
# [1/4] 加载 Docker 镜像
# =============================================================================
echo ""
echo -e "${GREEN}[1/4] 加载 Docker 镜像${NC}"

IMAGE_TAR="$BUNDLE_DIR/images/creditwise-latest.tar"
if [ ! -f "$IMAGE_TAR" ]; then
    echo -e "${RED}镜像文件不存在: $IMAGE_TAR${NC}"
    echo "请确认离线包已正确解压。"
    exit 1
fi

echo "  加载 creditwise:latest ($(du -sh "$IMAGE_TAR" | cut -f1)) ..."
docker load -i "$IMAGE_TAR"
echo -e "${GREEN}  ✅ 镜像加载完成${NC}"

# =============================================================================
# [2/4] 选择部署模式
# =============================================================================
echo ""
echo -e "${GREEN}[2/4] 选择部署模式${NC}"
echo ""
echo "  [1] 单用户模式 — 无需登录认证"
echo "  [2] 内网多用户 — Basic Auth 认证"
echo ""
read -p "请选择 [1/2] (默认: 2): " DEPLOY_MODE
DEPLOY_MODE=${DEPLOY_MODE:-2}

if [ "$DEPLOY_MODE" = "2" ]; then
    ENABLE_AUTH=true
    MODE_LABEL="内网多用户模式"
else
    ENABLE_AUTH=false
    MODE_LABEL="单用户模式"
fi
echo -e "${GREEN}已选择: ${MODE_LABEL}${NC}"

# =============================================================================
# [3/4] 配置环境
# =============================================================================
echo ""
echo -e "${GREEN}[3/4] 配置环境${NC}"

cd "$PROJECT_ROOT"

# .env 文件
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
        echo "  从 .env.example 创建 .env"
    else
        touch "$ENV_FILE"
        echo "  创建空 .env"
    fi
fi

# 设置 ENABLE_AUTH
if grep -q '^ENABLE_AUTH=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^ENABLE_AUTH=.*|ENABLE_AUTH=${ENABLE_AUTH}|" "$ENV_FILE"
else
    echo "ENABLE_AUTH=${ENABLE_AUTH}" >> "$ENV_FILE"
fi
echo "  ENABLE_AUTH=${ENABLE_AUTH}"

# 自动生成加密密钥（如果未设置）
if ! grep -q '^LLM_MANAGER_ENCRYPTION_KEY=.\+' "$ENV_FILE" 2>/dev/null; then
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
                     openssl rand -base64 32 2>/dev/null || \
                     echo "")
    if [ -n "$ENCRYPTION_KEY" ]; then
        echo "LLM_MANAGER_ENCRYPTION_KEY=${ENCRYPTION_KEY}" >> "$ENV_FILE"
        echo "  已自动生成 LLM_MANAGER_ENCRYPTION_KEY"
    else
        echo -e "${YELLOW}  ⚠️  无法自动生成加密密钥，请手动在 .env 中设置 LLM_MANAGER_ENCRYPTION_KEY${NC}"
    fi
fi

# 多用户配置
if [ "$ENABLE_AUTH" = "true" ]; then
    if [ ! -f "$PROJECT_ROOT/config/users.yaml" ] && [ -f "$PROJECT_ROOT/config/users.yaml.example" ]; then
        cp "$PROJECT_ROOT/config/users.yaml.example" "$PROJECT_ROOT/config/users.yaml"
        echo -e "${YELLOW}  ⚠️  请编辑 config/users.yaml 配置用户账号和密码${NC}"
        echo "     生成密码哈希: python scripts/hash_password.py <密码>"
    fi
fi

# 确保运行时目录存在
mkdir -p workspace execution_states task_results logs config

# 预创建数据库文件（避免 Docker bind mount 将其创建为目录）
for DB_FILE in llm_manager.db task_manager.db; do
    [ -f "$PROJECT_ROOT/$DB_FILE" ] || touch "$PROJECT_ROOT/$DB_FILE"
done

echo -e "${GREEN}  ✅ 环境配置完成${NC}"

# =============================================================================
# [4/4] 启动服务（不 build，直接使用已加载的镜像）
# =============================================================================
echo ""
echo -e "${GREEN}[4/4] 启动服务${NC}"

cd "$PROJECT_ROOT/docker"
ENABLE_AUTH=${ENABLE_AUTH} docker compose up -d

echo ""
echo "等待服务启动..."
for i in $(seq 1 12); do
    if curl -sf http://localhost:8200/health > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ 服务启动成功！${NC}"
        break
    fi
    if [ $i -eq 12 ]; then
        echo -e "${YELLOW}  ⚠️  服务可能未完全启动，请检查日志: docker compose logs${NC}"
    fi
    sleep 5
done

SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "============================================================"
echo -e "${GREEN} 部署完成！${NC}"
echo "============================================================"
echo ""
echo " 访问地址: http://${SERVER_IP}:8200"
echo " API 文档: http://${SERVER_IP}:8200/docs"
echo " 部署模式: ${MODE_LABEL}"
echo ""
echo " 常用命令:"
echo "   查看日志:   cd docker && docker compose logs -f"
echo "   停止服务:   cd docker && docker compose down"
echo "   重启服务:   cd docker && ENABLE_AUTH=${ENABLE_AUTH} docker compose restart"
echo ""
echo "============================================================"
