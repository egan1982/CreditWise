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
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制项目代码
COPY API/ ./API/
COPY deepanalyze/ ./deepanalyze/
COPY llm_manager_integrated/ ./llm_manager_integrated/
COPY scripts/ ./scripts/
COPY config/users.yaml.example ./config/users.yaml.example
COPY run.py .
COPY deepanalyze.py .
COPY .env.example ./.env.example

# 复制前端构建产物到 LLM Manager 静态目录
# （生产模式下 FastAPI 直接提供静态文件）
COPY --from=frontend-builder /build/.next ./demo/chat/.next
COPY --from=frontend-builder /build/public ./demo/chat/public

# 创建必要的目录
RUN mkdir -p workspace execution_states task_results logs config

# 暴露端口
EXPOSE 8200 8100

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8200/health || exit 1

# 启动命令
CMD ["python", "API/main.py"]
