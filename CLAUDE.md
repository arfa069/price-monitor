# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供代码库操作指南。

# 执行任何命令前必读⚠️ 
在运行任何 shell / test / lint 命令之前，**必须**先查看本文件第 3 节的"常用命令"，
确认正确的执行方式。默认不在 PATH 中的工具，必须通过 `powershell.exe` 调用。

## 1.始终加载Karpathy编码准则⚠️ 
Always load the `karpathy-guidelines` skill when coding.

## 2.项目概览

淘宝、京东、亚马逊价格监控系统 + Boss 直聘职位搜索监控。通过 Playwright 抓取商品页面/职位信息，记录价格历史，降价时通过飞书 Webhook 发送通知。
**技术栈**：Python 3.11+ · FastAPI · PostgreSQL (async SQLAlchemy) · Redis · Playwright · 飞书 Webhook
**前端**：React + Vite + TypeScript + Ant Design + Figma Design System（黑白核心 + 马卡龙色块 + 胶囊按钮）

## 3.常用命令

### 安装依赖
powershell.exe -Command "cd C:/Users/arfac/price-monitor/backend; pip install -e ."

### 运行数据库迁移
powershell.exe -Command "cd C:/Users/arfac/price-monitor/backend; alembic upgrade head"

### 启动前端服务器和后端服务器
powershell.exe -Command "cd C:/Users/arfac/price-monitor; powershell -ExecutionPolicy Bypass -File 'scripts/start_server.ps1'"

### 运行测试
powershell.exe -Command "cd C:/Users/arfac/price-monitor/backend; pytest"

### 代码检查
powershell.exe -Command "cd C:/Users/arfac/price-monitor/backend; ruff check ."

## 4.后端架构
→ 详见 doc/backend-architecture.md
→ 权限架构详见 doc/permission-architecture.md

## 5.前端架构
→ 详见 doc/frontend-architecture.md

## 6.关键约定
- user_id 硬编码为 1（单用户系统）已添加多用户认证，原有 user_id=1 硬编码仍适用于商品/职位爬取
- 系统的测试用户: default123 密码:123456
- 所有时间戳字段使用 UTC 时区（`datetime.now(timezone.utc)`）
- 价格比较使用 Decimal 避免浮点误差
- LLM provider 通过 `LLMProviderFactory` 切换，支持 Anthropic/OpenAI/Ollama

## 7.本地开发及验证流程
- 「改 → 构建 → 启动 → 验证」完整闭环
- 所有测试必须先重启前后端

## 8. Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.
