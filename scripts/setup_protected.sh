#!/bin/bash
# =============================================================================
# 预编译代码包 — 首次部署环境初始化
# 用法:
#   chmod +x scripts/setup_protected.sh
#   ./scripts/setup_protected.sh              # 仅初始化环境
#   ./scripts/setup_protected.sh --build      # 初始化 + docker build + save镜像
#                                              （用于目标服务器无外网场景）
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

BUILD_MODE=false
if [ "$1" = "--build" ]; then
    BUILD_MODE=true
fi

echo "============================================================"
echo " CreditWise 预编译代码包 — 环境初始化"
echo "============================================================"

# 1. .env 文件
if [ ! -f .env ]; then
    echo "ENABLE_AUTH=true" > .env
    echo "创建 .env (ENABLE_AUTH=true)"
else
    if ! grep -q '^ENABLE_AUTH=' .env 2>/dev/null; then
        echo "ENABLE_AUTH=true" >> .env
    fi
fi

# 2. 加密密钥（LLM Manager 加密 API Key 存储必需）
if ! grep -q '^LLM_MANAGER_ENCRYPTION_KEY=.\+' .env 2>/dev/null; then
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
                     openssl rand -base64 32 2>/dev/null || \
                     echo "")
    if [ -n "$ENCRYPTION_KEY" ]; then
        echo "LLM_MANAGER_ENCRYPTION_KEY=${ENCRYPTION_KEY}" >> .env
        echo "已自动生成加密密钥"
    fi
fi

# 3. 预创建数据库文件（Docker bind mount 需文件存在，否则会创建为目录）
for DB_FILE in llm_manager.db task_manager.db; do
    if [ ! -f "$DB_FILE" ]; then
        touch "$DB_FILE"
        echo "创建 $DB_FILE"
    fi
done

# 4. 确保运行时目录存在
mkdir -p workspace execution_states task_results logs config

# 5. 删除用户配置模板（否则含占位符哈希会阻塞 admin 自动引导）
rm -f config/users.yaml

# 6. 修复 Dockerfile Python 版本：.so 编译于 Python 3.11，Dockerfile 需对齐
if grep -q 'python:3.12-slim' docker/Dockerfile 2>/dev/null; then
    sed -i 's/python:3.12-slim/python:3.11-slim/g' docker/Dockerfile
    echo "Dockerfile Python 版本已对齐编译环境 (3.12→3.11)"
fi

# 7. --build 模式：构建 Docker 镜像 + 导出 + 生成离线部署包（用于目标服务器无外网场景）
if [ "$BUILD_MODE" = "true" ]; then
    echo ""
    echo "===[--build] 构建 Docker 镜像==="
    docker compose -f docker/docker-compose.yml build

    echo ""
    echo "===[--build] 导出镜像==="
    mkdir -p images
    docker save creditwise:latest -o images/creditwise-latest.tar
    echo "镜像已导出: images/creditwise-latest.tar ($(du -sh images/creditwise-latest.tar | cut -f1))"

    echo ""
    echo "===[--build] 生成离线部署包==="
    BUNDLE_DIR="/tmp/creditwise_offline_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BUNDLE_DIR/images" "$BUNDLE_DIR/source/docker" \
             "$BUNDLE_DIR/source/scripts" "$BUNDLE_DIR/source/config"

    cp images/creditwise-latest.tar "$BUNDLE_DIR/images/"
    cp docker/docker-compose.yml "$BUNDLE_DIR/source/docker/"
    cp .env "$BUNDLE_DIR/source/" 2>/dev/null || true
    cp config/users.yaml.example "$BUNDLE_DIR/source/config/" 2>/dev/null || true
    cp scripts/deploy_offline.sh "$BUNDLE_DIR/source/scripts/"

    ARCHIVE_NAME="creditwise_offline_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "$ARCHIVE_NAME" -C "$BUNDLE_DIR" .
    rm -rf "$BUNDLE_DIR"

    echo ""
    echo "============================================================"
    echo " 环境初始化 + 镜像构建 + 离线包打包完成"
    echo "============================================================"
    echo " 离线包: $PWD/$ARCHIVE_NAME ($(du -sh $ARCHIVE_NAME | cut -f1))"
    echo ""
    echo " 将此文件传输到目标无外网服务器后执行:"
    echo "   tar -xzf $ARCHIVE_NAME"
    echo "   cd offline_bundle/source"
    echo "   chmod +x scripts/deploy_offline.sh"
    echo "   ./scripts/deploy_offline.sh"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo " 环境初始化完成"
    echo "============================================================"
    echo " 下一步: docker compose -f docker/docker-compose.yml up -d"
    echo ""
    echo "（若目标服务器无外网，请使用: ./scripts/setup_protected.sh --build）"
    echo "============================================================"
fi
