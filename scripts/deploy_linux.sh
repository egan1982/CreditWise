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

echo -e "${GREEN}[1/7] 检查 Docker 环境${NC}"
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
echo -e "${GREEN}[2/7] 检查用户配置${NC}"
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
echo -e "${GREEN}[3/7] 检查环境配置${NC}"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        echo -e "${YELLOW}.env 不存在，从模板创建...${NC}"
        cp "$ENV_EXAMPLE" "$ENV_FILE"
    else
        echo -e "${YELLOW}.env.example 不存在，创建最小配置...${NC}"
        touch "$ENV_FILE"
    fi
fi

# 自动生成加密密钥（如果 .env 中没有设置）
if ! grep -q '^LLM_MANAGER_ENCRYPTION_KEY=.\+' "$ENV_FILE" 2>/dev/null; then
    echo -e "${YELLOW}LLM_MANAGER_ENCRYPTION_KEY 未配置，自动生成...${NC}"
    # 优先用 Python 生成 Fernet 密钥，如果 Python 不可用则用 openssl
    if command -v python3 &> /dev/null && python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
        NEW_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    elif command -v openssl &> /dev/null; then
        NEW_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
        # openssl 生成的不是标准 Fernet 密钥，需要用 Docker 构建后再生成
        echo -e "${YELLOW}⚠️  将在 Docker 构建后使用容器生成标准 Fernet 密钥${NC}"
        NEED_REGEN_KEY=true
    else
        echo -e "${RED}无法生成加密密钥（需要 python3+cryptography 或 openssl）${NC}"
        exit 1
    fi

    if [ "$NEED_REGEN_KEY" != "true" ]; then
        # 替换 .env 中的空值，或追加
        if grep -q '^LLM_MANAGER_ENCRYPTION_KEY=' "$ENV_FILE" 2>/dev/null; then
            sed -i "s|^LLM_MANAGER_ENCRYPTION_KEY=.*|LLM_MANAGER_ENCRYPTION_KEY=${NEW_KEY}|" "$ENV_FILE"
        else
            echo "LLM_MANAGER_ENCRYPTION_KEY=${NEW_KEY}" >> "$ENV_FILE"
        fi
        echo -e "${GREEN}✅ 加密密钥已自动生成并写入 .env${NC}"
    fi
else
    echo -e "${GREEN}加密密钥已配置${NC}"
fi

echo -e "${GREEN}环境配置: $ENV_FILE${NC}"

echo ""
echo -e "${GREEN}[4/7] 预创建数据库文件${NC}"
# Docker bind mount 要求宿主机上的文件必须存在，否则会被创建为目录导致 SQLite 报错
for DB_FILE in llm_manager.db task_manager.db; do
    DB_PATH="$PROJECT_ROOT/$DB_FILE"
    if [ ! -f "$DB_PATH" ]; then
        touch "$DB_PATH"
        echo -e "${GREEN}创建 $DB_FILE${NC}"
    else
        echo -e "${GREEN}$DB_FILE 已存在${NC}"
    fi
done

echo ""
echo -e "${GREEN}[5/7] 构建 Docker 镜像${NC}"
cd "$PROJECT_ROOT/docker"
echo "构建中，首次可能需要 5-10 分钟..."
docker-compose build

# 如果之前用 openssl 生成了临时密钥，现在用容器生成标准 Fernet 密钥
if [ "$NEED_REGEN_KEY" = "true" ]; then
    echo -e "${YELLOW}使用容器生成标准 Fernet 加密密钥...${NC}"
    NEW_KEY=$(docker-compose run --rm creditwise python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null | tail -1)
    if [ -n "$NEW_KEY" ]; then
        if grep -q '^LLM_MANAGER_ENCRYPTION_KEY=' "$PROJECT_ROOT/.env" 2>/dev/null; then
            sed -i "s|^LLM_MANAGER_ENCRYPTION_KEY=.*|LLM_MANAGER_ENCRYPTION_KEY=${NEW_KEY}|" "$PROJECT_ROOT/.env"
        else
            echo "LLM_MANAGER_ENCRYPTION_KEY=${NEW_KEY}" >> "$PROJECT_ROOT/.env"
        fi
        echo -e "${GREEN}✅ 加密密钥已生成并写入 .env${NC}"
    else
        echo -e "${RED}⚠️  无法生成密钥，请手动配置 .env 中的 LLM_MANAGER_ENCRYPTION_KEY${NC}"
    fi
fi

echo ""
echo -e "${GREEN}[6/7] 启动服务${NC}"
ENABLE_AUTH=true docker-compose up -d

echo ""
echo -e "${GREEN}[7/7] 验证服务${NC}"
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
