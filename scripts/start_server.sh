#!/usr/bin/env bash
# 自动启动后端服务器脚本

set -e

cd "$(dirname "$0")"

echo "正在启动价格监控系统后端..."

# 检查数据库连接
python -c "import asyncio; from app.database import engine; asyncio.run(engine.connect())" 2>/dev/null || {
    echo "警告: 数据库连接失败，请确保 PostgreSQL 已启动"
}

# 启动 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000