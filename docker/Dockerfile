# ============================================
# CreditWise 信贷风控智能助手 Docker Environment
# 支持两种模式：
#   - 私有化单用户（默认）
#   - 内网多用户（ENABLE_AUTH=true）
# ============================================

# Stage 1: 构建前端 (Next.js + LLM Manager)
FROM node:18-slim AS frontend-builder

# --- Next.js 主前端 ---
WORKDIR /build
COPY demo/chat/package.json demo/chat/package-lock.json* ./
RUN npm install --production=false
COPY demo/chat/ ./
RUN npm run build

# --- LLM Manager 前端完整构建 (Vite + Tailwind CSS) ---
# OFFLINE_MODE=true 时使用 pre-compiled 产物（prepare_offline.sh），跳过 npm
ARG OFFLINE_MODE=false
RUN mkdir -p /build-llm/frontend /build-llm/static
COPY llm_manager_integrated/frontend/package.json llm_manager_integrated/frontend/package-lock.json* /build-llm/frontend/
WORKDIR /build-llm/frontend
RUN if [ "$OFFLINE_MODE" != "true" ]; then \
        npm install --production=false; fi
COPY llm_manager_integrated/frontend/ /build-llm/frontend/
RUN if [ "$OFFLINE_MODE" != "true" ]; then \
        npm run build && \
        # Vite build 输出了编译后的 JS 到 ../static/assets/
        # publicDir 已禁用，手动复制 shared/ 和 scripts/ 到输出目录
        cp -r ../../shared ../static/ 2>/dev/null || true && \
        cp -r ./shared ../static/ 2>/dev/null || true && \
        cp -r ./scripts ../static/ 2>/dev/null || true && \
        npx tailwindcss -i ./styles/main.css -o ../static/assets/main.css --minify \
            --content "../static/index.html" --content "./scripts/**/*.js" && \
        # 修复 HTML 中的路径和 CDN 引用
        sed -i 's|<script src="https://cdn.tailwindcss.com.*></script>|<link rel="stylesheet" href="/llm-manager/assets/main.css">|' ../static/index.html && \
        sed -i 's|https://cdn.tailwindcss.com;||g' ../static/index.html && \
        sed -i 's|src="/static/scripts/main.js">|src="/llm-manager/scripts/main.js">|g' ../static/index.html && \
        sed -i 's|href="/static/shared/|href="/llm-manager/shared/|g' ../static/index.html && \
        sed -i 's|src="/static/shared/|src="/llm-manager/shared/|g' ../static/index.html && \
        # 移除内联 @apply 样式（已在 styles/main.css 中由 Tailwind CLI 编译）
        sed -i '/@apply/d' ../static/index.html; \
    fi

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
# 在线模式: pip install -r requirements.txt（从 PyPI）
# 离线模式: deploy_offline.sh 会将 wheels 填充到 .offline_wheels/ 目录
ARG OFFLINE_MODE=false
COPY requirements.txt .
COPY docker/.offline_wheels/ /tmp/offline_wheels/
RUN pip install --upgrade pip && \
    if [ "$OFFLINE_MODE" = "true" ] && ls /tmp/offline_wheels/*.whl >/dev/null 2>&1; then \
        echo "==> 离线模式: 使用本地 wheels"; \
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

# 复制前端构建产物（Next.js static export + LLM Manager Vite 编译）
# 生产模式下 FastAPI 直接提供静态文件
COPY --from=frontend-builder /build/dist ./demo/chat/dist
COPY --from=frontend-builder /build-llm/static/ ./llm_manager_integrated/static/

# 创建必要的目录
RUN mkdir -p workspace execution_states task_results logs config

# 暴露端口
EXPOSE 8200 8100

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8200/health || exit 1

# 启动命令
CMD ["python", "API/main.py"]
