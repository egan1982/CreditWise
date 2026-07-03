#!/bin/bash
# =============================================================================
# CreditWise 非 Docker 部署脚本（Linux / macOS）
#
# 用法：
#   chmod +x scripts/deploy_manual.sh
#   ./scripts/deploy_manual.sh
#
# 前置条件：
#   - Python ≥ 3.10
#   - Node.js ≥ 18（如需构建前端）
#   - kaleido Chromium 系统库（Linux）
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo " CreditWise 非 Docker 手动部署"
echo "============================================================"
echo ""

# =============================================================================
# [0] 部署模式
# =============================================================================
echo -e "${GREEN}[0] 选择部署模式${NC}"
echo "  [1] 单用户模式"
echo "  [2] 内网多用户（Basic Auth）"
read -p "请选择 [1/2] (默认: 1): " DEPLOY_MODE
DEPLOY_MODE=${DEPLOY_MODE:-1}

if [ "$DEPLOY_MODE" = "2" ]; then
    ENABLE_AUTH=true
else
    ENABLE_AUTH=false
fi

# =============================================================================
# [1] 系统依赖检查
# =============================================================================
echo -e "${GREEN}[1] 系统依赖检查${NC}"

# Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 未安装${NC}"
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo -e "${RED}✗ Python ≥ 3.10 需要（当前 $PY_VER）${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Python $PY_VER${NC}"

# Node.js（仅构建前端时需要）
HAS_NODE=false
if command -v node &> /dev/null; then
    NODE_VER=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        HAS_NODE=true
        echo -e "${GREEN}  ✓ Node.js $NODE_VER${NC}"
    else
        echo -e "${YELLOW}  ⚠️ Node.js $NODE_VER（需要 ≥ 18），将跳过前端构建${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠️ Node.js 未安装，将跳过前端构建${NC}"
fi

# kaleido Chromium 系统库（Linux）
if [ "$(uname)" = "Linux" ]; then
    for pkg in libgbm1 libnss3 libnspr4 libatk-bridge2.0-0 libatk1.0-0 libasound2 libxcomposite1 libxdamage1 libxrandr2 libxkbcommon0 libpango-1.0-0 libcups2; do
        if ! dpkg -s "$pkg" &>/dev/null 2>&1; then
            echo -e "${RED}✗ 缺失系统包: $pkg${NC}"
            echo "  Debian/Ubuntu: sudo apt-get install -y $pkg"
            echo "  CentOS/RHEL: sudo yum install -y mesa-libgbm nss nspr atk at-spi2-atk cups-libs libdrm libXcomposite libXdamage libXrandr pango"
        fi
    done
fi
echo -e "${GREEN}  ✓ 系统依赖检查完成${NC}"

# 端口
for PORT in 8200 8100; do
    if ss -tlnp 2>/dev/null | grep -q ":${PORT} " || lsof -i :${PORT} &>/dev/null 2>&1; then
        echo -e "${RED}✗ 端口 ${PORT} 已被占用${NC}"
        exit 1
    fi
done
echo -e "${GREEN}  ✓ 端口 8200, 8100 可用${NC}"

# =============================================================================
# [2] 创建虚拟环境
# =============================================================================
echo -e "${GREEN}[2] 创建 Python 虚拟环境${NC}"
cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}  ✅ Python 依赖安装完成${NC}"

# =============================================================================
# [3] 构建前端
# =============================================================================
echo -e "${GREEN}[3] 构建前端${NC}"

if [ "$HAS_NODE" = true ]; then
    # 主前端 (Next.js)
    if [ -f "demo/chat/package.json" ]; then
        echo "  构建主前端..."
        cd "$PROJECT_ROOT/demo/chat"
        npm install
        npm run build
        cd "$PROJECT_ROOT"
        echo -e "${GREEN}  ✓ 主前端构建完成${NC}"
    fi
    # LLM Manager 前端 (Vite JS + Tailwind CSS)
    if [ -f "llm_manager_integrated/frontend/package.json" ]; then
        echo "  构建 LLM Manager 前端（Vite + Tailwind）..."
        cd "$PROJECT_ROOT/llm_manager_integrated/frontend"
        npm install
        npm run build 2>/dev/null || echo -e "${YELLOW}  ⚠️ Vite 构建失败${NC}"
        npx tailwindcss -i ./styles/main.css -o "$PROJECT_ROOT/llm_manager_integrated/static/assets/main.css" --minify \
            --content "./index.html" \
            --content "./scripts/**/*.js" \
            --content "./shared/**/*.js" 2>/dev/null
        sed -i 's|<script src="https://cdn.tailwindcss.com[^"]*"></script>|<link rel="stylesheet" href="/llm-manager/assets/main.css">|' "$PROJECT_ROOT/llm_manager_integrated/static/assets/index.html"
        sed -i 's| https://cdn.tailwindcss.com||g' "$PROJECT_ROOT/llm_manager_integrated/static/assets/index.html"
        sed -i 's|http://localhost:8200 ||g' "$PROJECT_ROOT/llm_manager_integrated/static/assets/index.html"
        sed -i '/<style>/,/<\/style>/d' "$PROJECT_ROOT/llm_manager_integrated/static/assets/index.html"
        cd "$PROJECT_ROOT"
    fi
else
    echo -e "${YELLOW}  ⚠️ 跳过前端构建（Node.js 不可用），使用已有构建产物或 dev server${NC}"
fi

# =============================================================================
# [4] 配置环境
# =============================================================================
echo -e "${GREEN}[4] 配置环境${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# ENABLE_AUTH
if grep -q '^ENABLE_AUTH=' .env 2>/dev/null; then
    sed -i.bak "s|^ENABLE_AUTH=.*|ENABLE_AUTH=${ENABLE_AUTH}|" .env && rm -f .env.bak
else
    echo "ENABLE_AUTH=${ENABLE_AUTH}" >> .env
fi

# 加密密钥
if grep -q '^LLM_MANAGER_ENCRYPTION_KEY=.\+' .env 2>/dev/null; then
    echo -e "${GREEN}  ✓ 加密密钥已配置${NC}"
else
    echo -e "${YELLOW}  ⚠️ LLM_MANAGER_ENCRYPTION_KEY 未设置，已自动生成${NC}"
    KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "LLM_MANAGER_ENCRYPTION_KEY=${KEY}" >> .env
fi

# 多用户配置
# CVM部署测试发现（2026-07-03）：原逻辑无论 config/users.yaml 是否已存在都会
# 打印"请编辑"提示，容易让运维误以为账户尚未配置——实际上零配置自动兜底逻辑
# （API/main.py::_ensure_bootstrap_admin_if_empty）已能在 users.yaml 不存在时
# 自动创建初始admin账户，这里区分两种情况给出准确提示。
if [ "$ENABLE_AUTH" = "true" ]; then
    if [ -f "config/users.yaml" ]; then
        echo -e "${GREEN}  ✓ 用户配置已存在: config/users.yaml${NC}"
    else
        echo -e "${GREEN}  ✓ 未配置 users.yaml，将由零配置自动兜底逻辑生成初始admin账户（首次启动后查看 logs/server.log 获取一次性密码）${NC}"
    fi
fi

# 预创建目录
mkdir -p workspace execution_states task_results logs

# =============================================================================
# [5] 启动
# =============================================================================
echo -e "${GREEN}[5] 启动服务${NC}"
echo "启动后端 (端口 8200)..."
# CVM部署测试发现（2026-07-03）：此前未显式设置 DEV_MODE，而 API/main.py 中
# `os.getenv("DEV_MODE", "true")` 默认值为 "true"（开发模式）——导致非Docker
# 手动部署默认以开发模式启动：① 主应用 "/" 不会返回 demo/chat/dist/index.html
# 构建产物，而是返回纯JSON状态信息；② LLM Manager 子系统会认为前端跑在
# Vite dev server(:3001)，但手动部署场景下该dev server并未启动。显式导出
# DEV_MODE=false，与 docs/intranet_deployment_guide.md §4.2 描述的生产部署
# 行为对齐。
export DEV_MODE=false
export API_HOST=0.0.0.0
nohup python API/main.py > logs/server.log 2>&1 &
PID=$!
echo "  进程 PID: $PID"
echo "  日志: logs/server.log"

sleep 3
if curl -sf http://localhost:8200/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务启动成功！${NC}"
else
    echo -e "${RED}⚠️  服务启动可能失败，请检查日志${NC}"
fi

echo ""
echo "============================================================"
echo -e "${GREEN} 部署完成！${NC}"
echo "============================================================"
echo ""
echo " 访问地址: http://localhost:8200"
echo " 停止服务: kill $PID"
echo ""
