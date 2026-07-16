#!/bin/bash
# =============================================================================
# 预编译代码包 — 首次部署环境初始化
# 用法: chmod +x scripts/setup_protected.sh && ./scripts/setup_protected.sh
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

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

echo ""
echo "============================================================"
echo " 环境初始化完成"
echo "============================================================"
echo " 下一步: docker compose up -d"
echo "============================================================"
