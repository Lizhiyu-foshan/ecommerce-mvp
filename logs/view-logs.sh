#!/bin/bash
# 日志查看工具

LOG_DIR="/root/.openclaw/workspace/projects/ecommerce-mvp/logs"

show_help() {
    echo "日志查看工具"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -a, --app       查看应用日志 (app.log)"
    echo "  -e, --error     查看错误日志 (error.log)"
    echo "  -c, --access    查看访问日志 (access.log)"
    echo "  -f, --follow    实时跟踪日志"
    echo "  -n, --lines N   显示最后N行 (默认50)"
    echo "  -h, --help      显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 -a           # 查看应用日志"
    echo "  $0 -e -f        # 实时跟踪错误日志"
    echo "  $0 -a -n 100    # 查看应用日志最后100行"
}

# 默认参数
LOG_FILE="app.log"
LINES=50
FOLLOW=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--app)
            LOG_FILE="app.log"
            shift
            ;;
        -e|--error)
            LOG_FILE="error.log"
            shift
            ;;
        -c|--access)
            LOG_FILE="access.log"
            shift
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查日志目录
if [ ! -d "$LOG_DIR" ]; then
    echo "❌ 日志目录不存在: $LOG_DIR"
    exit 1
fi

# 检查日志文件
LOG_PATH="$LOG_DIR/$LOG_FILE"
if [ ! -f "$LOG_PATH" ]; then
    echo "⚠️ 日志文件不存在: $LOG_PATH"
    echo "可用的日志文件:"
    ls -lh "$LOG_DIR"/*.log 2>/dev/null || echo "  无日志文件"
    exit 1
fi

# 显示日志信息
echo "=========================================="
echo "📄 查看日志: $LOG_FILE"
echo "📍 位置: $LOG_PATH"
echo "📊 大小: $(ls -lh "$LOG_PATH" | awk '{print $5}')"
echo "=========================================="
echo ""

# 查看日志
if [ "$FOLLOW" = true ]; then
    echo "🔄 实时跟踪日志 (按 Ctrl+C 退出)..."
    tail -f "$LOG_PATH"
else
    echo "📝 最后 $LINES 行日志:"
    echo ""
    tail -n "$LINES" "$LOG_PATH"
fi
