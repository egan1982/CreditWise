#!/bin/bash
# =============================================================================
# CreditWise Docker 服务管理脚本
#
# 用法：
#   ./scripts/service.sh start    # 启动（内网多用户模式）
#   ./scripts/service.sh stop     # 停止
#   ./scripts/service.sh restart  # 重启
#   ./scripts/service.sh status   # 查看状态
#   ./scripts/service.sh logs     # 查看日志
#   ./scripts/service.sh build    # 重新构建镜像
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

cd "$DOCKER_DIR"

case "$1" in
    start)
        echo "启动 CreditWise（认证模式）..."
        ENABLE_AUTH=true docker-compose up -d
        echo "服务已启动，访问: http://$(hostname -I | awk '{print $1}'):8200"
        ;;
    start-noauth)
        echo "启动 CreditWise（无认证模式）..."
        docker-compose up -d
        echo "服务已启动（无认证），访问: http://$(hostname -I | awk '{print $1}'):8200"
        ;;
    stop)
        echo "停止服务..."
        docker-compose down
        echo "服务已停止"
        ;;
    restart)
        echo "重启服务..."
        docker-compose down
        ENABLE_AUTH=true docker-compose up -d
        echo "服务已重启"
        ;;
    status)
        docker-compose ps
        echo ""
        curl -sf http://localhost:8200/health && echo " ← API 健康" || echo "API 未响应"
        ;;
    logs)
        docker-compose logs -f --tail=100
        ;;
    build)
        echo "重新构建镜像..."
        docker-compose build --no-cache
        echo "构建完成，使用 ./service.sh start 启动"
        ;;
    hash)
        shift
        docker-compose run --rm creditwise python scripts/hash_password.py "$@"
        ;;
    *)
        echo "用法: $0 {start|start-noauth|stop|restart|status|logs|build|hash}"
        echo ""
        echo "  start        启动服务（启用认证）"
        echo "  start-noauth 启动服务（无认证，私有化模式）"
        echo "  stop         停止服务"
        echo "  restart      重启服务"
        echo "  status       查看服务状态"
        echo "  logs         查看日志（实时跟踪）"
        echo "  build        重新构建镜像"
        echo "  hash <pwd>   生成密码哈希"
        exit 1
        ;;
esac
