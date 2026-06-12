# ============================================
# CreditWise 信贷风控智能助手 Docker Environment
# 支持两种模式：
#   - 私有化单用户（默认）
#   - 内网多用户（ENABLE_AUTH=true）
# ============================================

# Stage 1: 构建前端
FROM node:18-slim AS frontend-builder

WORKDIR /build

# 复制前端代码
COPY demo/chat/package.json demo/chat/package-lock.json* ./
RUN npm install --production=false

COPY demo/chat/ ./
RUN npm run build

# Stage 2: 运行时
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # 默认配置（可通过 docker-compose 或 docker run -e 覆盖）
    API_HOST=0.0.0.0 \
    API_PORT=8200 \
    DEV_MODE=false \
    ENABLE_AUTH=false

WORKDIR /app

# 安装系统依赖
# kaleido（Plotly→PNG渲染引擎）内置 Chromium，需要以下共享库
# 缺少这些库会导致 Word 报告中所有图表（ROC/KS/评分分布等）生成失败
RUN apt-get update && apt-get install -y \
    git \
    curl \
    # kaleido/Chromium 运行依赖
    libgbm1 \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libasound2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcups2 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
# 优先使用离线 wheel 包（deploy_offline.sh 场景），否则在线安装
COPY requirements.txt .
COPY offline_bundle/wheels/ /tmp/offline_wheels/ 2>/dev/null || true
RUN pip install --upgrade pip && \
    if [ -d /tmp/offline_wheels ] && ls /tmp/offline_wheels/*.whl >/dev/null 2>&1; then \
        echo "使用离线 wheel 安装..."; \
        pip install --no-index --find-links=/tmp/offline_wheels -r requirements.txt; \
    else \
        pip install -r requirements.txt; \
    fi

# 复制项目代码
COPY API/ ./API/
COPY deepanalyze/ ./deepanalyze/
COPY llm_manager_integrated/ ./llm_manager_integrated/
COPY scripts/ ./scripts/
COPY config/users.yaml.example ./config/users.yaml.example
COPY run.py .
COPY deepanalyze.py .

# 复制前端构建产物（Next.js static export 模式，输出到 dist/）
# 生产模式下 FastAPI 直接提供静态文件
COPY --from=frontend-builder /build/dist ./demo/chat/dist

# 创建必要的目录
RUN mkdir -p workspace execution_states task_results logs config

# 暴露端口
EXPOSE 8200 8100

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8200/health || exit 1

# 启动命令
CMD ["python", "API/main.py"]
