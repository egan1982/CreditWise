#!/bin/bash
# =============================================================================
# CreditWise 受保护部署包 — 一站式构建 + 端到端验证
#
# 用法：
#   ./scripts/build_protected.sh              # 完整流程：编译验证 → 镜像构建 → 打包 → 端到端验证
#   ./scripts/build_protected.sh --skip-verify # 跳过第4步端到端验证（仅用于快速迭代调试）
#
# 详见 docs/code-protection-plan.md §5.4、§6.1 实施时间线
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SKIP_VERIFY=false
[ "$1" = "--skip-verify" ] && SKIP_VERIFY=true

cd "$PROJECT_ROOT"

echo "============================================================"
echo " CreditWise 受保护部署包 — 一站式构建"
echo "============================================================"
echo ""

# =============================================================================
# [1/4] 本地 Cython 试编译验证
# （仅开发调试用，镜像内的编译在 Docker Stage 1 内独立完成）
# =============================================================================
echo -e "${GREEN}[1/4] 本地试编译验证${NC}"

if [ ! -f "$PROJECT_ROOT/build_cython.py" ]; then
    echo -e "${RED}  build_cython.py 不存在，请先创建编译脚本${NC}"
    exit 1
fi

# 检查 cython 是否已安装
python -c "import Cython" 2>/dev/null || {
    echo -e "${YELLOW}  Cython 未安装，跳过本地试编译（不影响最终镜像构建）${NC}"
    echo "  提示: pip install cython 可启用本地验证"
}

python build_cython.py --dry-run
echo ""
echo -e "${YELLOW}  提示: 上方为编译范围预览，如需实际本地试编译请手动执行:${NC}"
echo "    python build_cython.py --yes --replace"
echo "    pytest tests/ -x"
echo "    python build_cython.py --clean   # 验证完毕后恢复开发环境"
echo ""

if [ "$SKIP_VERIFY" != "true" ]; then
    read -p "是否已完成本地试编译验证（或确认跳过）？按回车继续..."
fi

# =============================================================================
# [2/4] Docker 编译版镜像构建 + 离线打包
# =============================================================================
echo ""
echo -e "${GREEN}[2/4] 构建受保护离线部署包${NC}"
echo "  调用: ./scripts/prepare_offline.sh --protected"
echo ""

if [ ! -x "$PROJECT_ROOT/scripts/prepare_offline.sh" ]; then
    chmod +x "$PROJECT_ROOT/scripts/prepare_offline.sh"
fi
./scripts/prepare_offline.sh --protected

# =============================================================================
# [3/4] 源码清理自检（镜像内验证，防止 Gap #3/#2 类问题回归）
# =============================================================================
echo ""
echo -e "${GREEN}[3/4] 镜像源码清理自检${NC}"

# 检查核心算法源码是否已清理
FOUND=$(docker run --rm creditwise:protected find /app -name "rule_mining.py" 2>/dev/null || true)
if [ -n "$FOUND" ]; then
    echo -e "${RED}  FAIL: 镜像内仍残留 rule_mining.py 源码，保护未生效${NC}"
    exit 1
fi
echo -e "${GREEN}  PASS: 核心算法源码已确认清理${NC}"

# 检查 .py.bak 残留
BAK_FOUND=$(docker run --rm creditwise:protected find /app -name "*.py.bak" 2>/dev/null || true)
if [ -n "$BAK_FOUND" ]; then
    echo -e "${RED}  FAIL: 镜像内残留 .py.bak 文件（Gap B 回归）${NC}"
    exit 1
fi
echo -e "${GREEN}  PASS: .py.bak 清理确认通过${NC}"

# =============================================================================
# [4/4] 离线部署端到端验证（模拟内网服务器环境）
# =============================================================================
echo ""
if [ "$SKIP_VERIFY" = "true" ]; then
    echo -e "${YELLOW}[4/4] 跳过端到端验证 (--skip-verify)${NC}"
else
    echo -e "${GREEN}[4/4] 离线部署端到端验证${NC}"
    echo "  解压 → docker load → docker compose up → health check"

    VERIFY_DIR="/tmp/creditwise_verify_$(date +%s)"
    mkdir -p "$VERIFY_DIR"

    ARCHIVE_NAME="creditwise_offline_bundle_protected.tar.gz"
    if [ ! -f "$PROJECT_ROOT/$ARCHIVE_NAME" ]; then
        echo -e "${RED}  FAIL: $ARCHIVE_NAME 不存在${NC}"
        exit 1
    fi

    echo "  解压 $ARCHIVE_NAME ..."
    tar -xzf "$PROJECT_ROOT/$ARCHIVE_NAME" -C "$VERIFY_DIR"
    cd "$VERIFY_DIR/offline_bundle/source"

    if [ -x scripts/deploy_offline.sh ]; then
        chmod +x scripts/deploy_offline.sh
    fi

    echo "  执行 deploy_offline.sh ..."
    ./scripts/deploy_offline.sh

    echo "  等待服务启动..."
    sleep 5

    # Health check
    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8200/health 2>/dev/null || echo "000")
    if [ "$HEALTH" != "200" ]; then
        echo -e "${RED}  FAIL: /health 返回 $HEALTH${NC}"
        echo "  检查容器状态: docker compose ps"
        cd "$PROJECT_ROOT"
        rm -rf "$VERIFY_DIR"
        exit 1
    fi
    echo -e "${GREEN}  PASS: /health 返回 200${NC}"

    # LLM Manager page check
    LLM_MGR=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://localhost:8200/llm-manager/ 2>/dev/null || echo "000")
    echo -e "${GREEN}  PASS: /llm-manager/ 返回 $LLM_MGR${NC}"

    # Cleanup
    cd "$PROJECT_ROOT"
    echo "  清理验证环境..."
    cd "$VERIFY_DIR/offline_bundle/source" && docker compose down 2>/dev/null || true
    rm -rf "$VERIFY_DIR"
fi

echo ""
echo "============================================================"
echo -e "${GREEN} 受保护部署包构建 + 验证全部完成${NC}"
echo "============================================================"
echo " 产出: $PROJECT_ROOT/creditwise_offline_bundle_protected.tar.gz"
echo "============================================================"
