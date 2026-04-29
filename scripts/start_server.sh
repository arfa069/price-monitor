#!/usr/bin/env bash
# 自动启动后端服务器脚本

set -e

cd "$(dirname "$0")/../backend"

echo "正在启动价格监控系统后端..."

# 启动 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
