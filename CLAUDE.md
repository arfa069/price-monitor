# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供代码库操作指南。


## 1.始终加载Karpathy编码准则
Always load the `karpathy-guidelines` skill when coding.

## 2.项目概览

淘宝、京东、亚马逊价格监控系统 + Boss 直聘职位搜索监控。通过 Playwright 抓取商品页面/职位信息，记录价格历史，降价时通过飞书 Webhook 发送通知。
**技术栈**：Python 3.11+ · FastAPI · PostgreSQL (async SQLAlchemy) · Redis · Playwright · 飞书 Webhook
**前端**：React + Vite + TypeScript + Ant Design

## 3.常用命令

# **Windows/WSL执行脚本**：WSL中优先用`powershell.exe`调用 Windows PowerShell
/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe -ExecutionPolicy Bypass -File

# 启动前端服务器和后端服务器
Windows环境：
powershell -ExecutionPolicy Bypass -File ".\scripts\start_server.ps1"
WSL环境：
/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe -ExecutionPolicy Bypass -File "C:/Users/arfac/price-monitor/scripts/start_server.ps1"

# 安装依赖
cd backend && pip install -e .

# 运行数据库迁移
cd backend && alembic upgrade head

# 启动开发服务器
cd backend && python -m uvicorn app.main:app
# 注意：Windows 上不要用 --reload，会导致 Playwright 子进程报错

# 运行测试
cd backend && pytest

# 代码检查
cd backend && ruff check .

# 启动前端
cd frontend && npm run dev

## 4.后端架构
→ 详见 doc/backend-architecture.md

## 5.前端架构
→ 详见 doc/frontend-architecture.md

## 6.关键约定
- user_id 硬编码为 1（单用户系统）已添加多用户认证，原有 user_id=1 硬编码仍适用于商品/职位爬取
- 所有时间戳字段使用 UTC 时区（`datetime.now(timezone.utc)`）
- 价格比较使用 Decimal 避免浮点误差
- LLM provider 通过 `LLMProviderFactory` 切换，支持 Anthropic/OpenAI/Ollama

## 7.本地开发及验证流程
- 「改 → 构建 → 启动 → 验证」完整闭环
- 所有测试必须先重启前后端
