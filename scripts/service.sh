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
        # 从 .env 读取 ENABLE_AUTH（docker-compose.yml 中该变量的 compose 级默认值是
        # true——不显式传递时，docker compose 会用其自身的默认值而非 .env 里的值，
        # 因此这里两个分支都必须显式 export，不能只在 true 分支传参）
        AUTH_VAL=$(grep -oP '^ENABLE_AUTH=\K.*' "$PROJECT_ROOT/.env" 2>/dev/null || echo "true")
        echo "启动 CreditWise（ENABLE_AUTH=${AUTH_VAL}）..."
        if [ "$AUTH_VAL" = "true" ]; then
            echo "  首次启动内网多用户模式：容器会自动创建初始admin账户，"
            echo "  完成后运行 './scripts/service.sh logs' 查看一次性密码"
            ENABLE_AUTH=true docker compose up -d
        else
            ENABLE_AUTH=false docker compose up -d
        fi
        echo "服务已启动，访问: http://$(hostname -I | awk '{print $1}'):8200"
        ;;
    stop)
        echo "停止服务..."
        docker compose down
        echo "服务已停止"
        ;;
    restart)
        # 从 .env 读取 ENABLE_AUTH（同 start，两分支都需显式 export）
        AUTH_VAL=$(grep -oP '^ENABLE_AUTH=\K.*' "$PROJECT_ROOT/.env" 2>/dev/null || echo "true")
        echo "重启服务（ENABLE_AUTH=${AUTH_VAL}）..."
        docker compose down
        if [ "$AUTH_VAL" = "true" ]; then
            ENABLE_AUTH=true docker compose up -d
        else
            ENABLE_AUTH=false docker compose up -d
        fi
        echo "服务已重启"
        ;;
    start-noauth)
        # 同 start 分支的坑：docker-compose.yml 里 ENABLE_AUTH 的 compose 级默认值是
        # true，不显式 export 的话这里也会被启动成"有认证"，与命令名字矛盾
        echo "启动 CreditWise（无认证模式）..."
        ENABLE_AUTH=false docker compose up -d
        echo "服务已启动（无认证），访问: http://$(hostname -I | awk '{print $1}'):8200"
        ;;
    status)
        docker compose ps
        echo ""
        curl -sf http://localhost:8200/health && echo " ← API 健康" || echo "API 未响应"
        ;;
    logs)
        docker compose logs -f --tail=100
        ;;
    build)
        echo "重新构建镜像..."
        docker compose build --no-cache
        echo "构建完成，使用 ./service.sh start 启动"
        ;;
    hash)
        shift
        docker compose run --rm creditwise python scripts/hash_password.py "$@"
        ;;
    *)
        echo "用法: $0 {start|start-noauth|stop|restart|status|logs|build|hash}"
        echo ""
        echo "  start        启动服务（启用认证，默认。首次启动零账户时自动生成初始admin，见logs）"
        echo "  start-noauth 启动服务（无认证，私有化模式）"
        echo "  stop         停止服务"
        echo "  restart      重启服务"
        echo "  status       查看服务状态"
        echo "  logs         查看日志（实时跟踪，含首次启动的初始admin一次性密码）"
        echo "  build        重新构建镜像"
        echo "  hash <pwd>   生成密码哈希（传统方式，需要自定义账户名/多账户时使用）"
        exit 1
        ;;
esac
