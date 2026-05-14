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

### 启动前端服务器和后端服务器 **前端端口3000，后端8000**
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
- 默认闭环：改动 → 检查/构建 → 重启服务 → 真实验证 → 报告证据。
- 命令执行前先看第 3 节，Windows 下优先使用 `powershell.exe -Command "..."`。
- 后端改动：运行相关 `pytest`；影响共享逻辑/权限/调度/爬虫/模型时运行完整 `pytest` 和 `ruff check .`。
- 前端改动：运行相关检查；提交前默认运行 `npm run lint` 和 `npm run build`。
- 涉及 UI/路由/弹窗/下拉/表单/权限/爬取触发时，必须启动前后端并用浏览器真实验证。
- 涉及爬虫登录态时，必须确认 Edge CDP 可用：`http://127.0.0.1:9222/json/version` 返回 `webSocketDebuggerUrl`。
- Boss/京东/淘宝等强反爬流程，默认用已登录的 Edge CDP 专用浏览器验证。
- 无法执行的验证必须说明原因；未实际执行的检查不得声称通过。

## 8. Design System
- 在做任何视觉或 UI 决策前，必须先阅读 `DESIGN.md`。
- 字体、颜色、间距、组件风格和整体美学方向均以 `DESIGN.md` 为准。
- 未经用户明确批准，不得偏离设计系统。
- 进行 UI 审查或 QA 时，必须指出任何不符合 `DESIGN.md` 的实现。
