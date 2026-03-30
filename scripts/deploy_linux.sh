#!/bin/bash
# =============================================================================
# CreditWise 内网多用户版 — Linux CVM Docker 部署脚本
#
# 用法：
#   chmod +x scripts/deploy_linux.sh
#   ./scripts/deploy_linux.sh
#
# 前置条件：
#   - Linux CVM（CentOS/Ubuntu/Debian）
#   - 有 root 或 sudo 权限
#   - 网络可访问（安装 Docker + pip 依赖）
# =============================================================================

set -e

echo "============================================================"
echo " CreditWise 内网多用户版 — Docker 部署"
echo "============================================================"
echo ""

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目根目录（脚本所在目录的上一级）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}[1/6] 检查 Docker 环境${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker 未安装，正在安装...${NC}"
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y docker docker-compose
    else
        echo -e "${RED}无法自动安装 Docker，请手动安装后重试${NC}"
        exit 1
    fi
    sudo systemctl enable docker
    sudo systemctl start docker
    echo -e "${GREEN}Docker 安装完成${NC}"
else
    echo -e "${GREEN}Docker 已安装: $(docker --version)${NC}"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}docker-compose 未安装，请手动安装${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}[2/6] 检查用户配置${NC}"
CONFIG_FILE="$PROJECT_ROOT/config/users.yaml"
CONFIG_EXAMPLE="$PROJECT_ROOT/config/users.yaml.example"

if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "$CONFIG_EXAMPLE" ]; then
        echo -e "${YELLOW}users.yaml 不存在，从模板创建...${NC}"
        cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
        echo -e "${YELLOW}⚠️  请编辑 $CONFIG_FILE 配置真实的用户账号和密码哈希${NC}"
        echo -e "${YELLOW}   生成密码哈希: docker run --rm -it creditwise python scripts/hash_password.py${NC}"
        echo ""
        read -p "是否现在配置用户？(y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vi} "$CONFIG_FILE"
        fi
    else
        echo -e "${RED}config/users.yaml.example 不存在，请检查项目完整性${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}用户配置已存在: $CONFIG_FILE${NC}"
fi

echo ""
echo -e "${GREEN}[3/6] 检查环境配置${NC}"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        echo -e "${YELLOW}.env 不存在，从模板创建...${NC}"
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo -e "${YELLOW}⚠️  请编辑 $ENV_FILE 配置 LLM API Key 等信息${NC}"
        echo ""
        read -p "是否现在配置？(y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vi} "$ENV_FILE"
        fi
    else
        echo -e "${YELLOW}.env.example 不存在，跳过（可通过 LLM Manager 页面在线配置）${NC}"
    fi
else
    echo -e "${GREEN}环境配置已存在: $ENV_FILE${NC}"
fi

echo ""
echo -e "${GREEN}[4/6] 构建 Docker 镜像${NC}"
cd "$PROJECT_ROOT/docker"
echo "构建中，首次可能需要 5-10 分钟..."
docker-compose build

echo ""
echo -e "${GREEN}[5/6] 启动服务${NC}"
ENABLE_AUTH=true docker-compose up -d

echo ""
echo -e "${GREEN}[6/6] 验证服务${NC}"
echo "等待服务启动..."
sleep 5

# 健康检查（最多等 30 秒）
for i in $(seq 1 6); do
    if curl -sf http://localhost:8200/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务启动成功！${NC}"
        break
    fi
    if [ $i -eq 6 ]; then
        echo -e "${RED}⚠️  服务可能未完全启动，请检查日志: docker-compose logs${NC}"
    fi
    echo "等待中... ($i/6)"
    sleep 5
done

# 获取服务器 IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================================"
echo -e "${GREEN} 部署完成！${NC}"
echo "============================================================"
echo ""
echo " 访问地址:  http://${SERVER_IP}:8200"
echo " 健康检查:  http://${SERVER_IP}:8200/health"
echo " API 文档:  http://${SERVER_IP}:8200/docs"
echo ""
echo " 管理命令:"
echo "   查看日志:    cd docker && docker-compose logs -f"
echo "   停止服务:    cd docker && docker-compose down"
echo "   重启服务:    cd docker && ENABLE_AUTH=true docker-compose up -d"
echo "   生成密码:    docker-compose run --rm creditwise python scripts/hash_password.py"
echo ""
echo " 认证信息:"
echo "   配置文件:    config/users.yaml"
echo "   认证模式:    Basic Auth（浏览器弹窗登录）"
echo ""
echo "============================================================"
