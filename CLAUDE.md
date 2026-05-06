# CLAUDE.md

强制用简体中文回复，强制思考过程也用简体中文!
此文件为 Claude Code (claude.ai/code) 提供代码库操作指南。

## 1.先思考，后编码
**不要假设。不要隐藏困惑。呈现权衡方案。**
在编写代码之前：
- 明确你的假设。如果不确定，提出疑问。
- 如果存在多种可能的解读，将它们列出——不要随意选定一种。
- 如果存在更简单的方案，要提出。在必要时可以反驳。
- 如果有任何不清楚的地方，停下来。明确指出困惑所在。向用户开口询问。

## 2.简洁至上
**用最少的代码解决问题。不写任何推测性内容。**
- 不添加任何未被要求的功能。
- 不因为只有一次调用就引入抽象层。
- 如果未被要求，不要加入“灵活性”或“可配置性”。
- 不为不可能发生的场景编写错误处理。
- 如果你写了 200 行而实际上 50 行就能搞定，那就重写。
自我提问：“资深工程师看了会评价'这有点过度复杂'吗？”如果答案是肯定的，那就简化。

## 3.精准修改
**只触碰必须改动的部分。只清理你自己造成的烂摊子。**
在编辑已有代码时：
- 不要顺手“优化”相邻的代码、注释或格式。
- 不要重构没出问题的部分。
- 遵循现有代码风格，即使你自己更常用另一种写法。
- 如果发现与当前任务无关的死代码，可以提出来——但不要删除它。
当你的改动制造了孤立的冗余部分时：
- 删除那些因为你的改动才变得无用的导入、变量或函数。
- 不要删除任何原本就存在的死代码（除非明确要求）。
检验标准：每一行被改动的代码，都应能直接追溯到用户的原始需求。

## 4.目标计划执行
**定义成功标准。循环直至验证通过。**
将任务转化为可验证的目标：
- “添加验证” → “先为无效输入编写测试，然后让测试通过”
- “修复这个 Bug” → “先写一个能复现该问题的测试，然后使其通过”
- “重构 X” → “确保重构前后所有现有测试均保持通过”
对于多步骤的任务，先制定简要计划：

```
1. [步骤] → 验证：[检查]
2. [步骤] → 验证：[检查]
3. [步骤] → 验证：[检查]
```
清晰明确的成功标准能让你在验证循环中自主推进。而模糊的标准（例如“让它能跑就行”）则需要你来来回回不断澄清。

---

## 项目概览

淘宝、京东、亚马逊价格监控系统 + Boss 直聘职位搜索监控。通过 Playwright 抓取商品页面/职位信息，记录价格历史，降价时通过飞书 Webhook 发送通知。
**技术栈**：Python 3.11+ · FastAPI · PostgreSQL (async SQLAlchemy) · Redis · Playwright · 飞书 Webhook
**前端**：React + Vite + TypeScript + Ant Design

## 常用命令

```powershell
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

```
## 架构

### 入口文件
- `backend/app/main.py` — FastAPI 应用工厂，含 lifespan、路由注册、/health 检查
- `backend/app/config.py` — Pydantic Settings，环境变量

### 前端路由
- `/jobs` — 职位管理（搜索配置 + 职位列表 + 全量/单配置爬取）
- `/products` — 商品管理（商品列表 + 商品爬取 + 爬取记录）
- `/schedule` — 定时配置（Cron 定时配置：商品 per-platform 表格 + 职位 per-config 表格；数据保留 + 飞书 Webhook 设置）
- `/login` — 登录页面
- `/register` — 注册页面

### 平台适配器模式
```
backend/app/platforms/base.py     — BasePlatformAdapter (ABC)：_init_browser、crawl、extract_price/title（抽象方法）
backend/app/platforms/taobao.py   — TaobaoAdapter
backend/app/platforms/jd.py       — JDAdapter
backend/app/platforms/amazon.py  — AmazonAdapter
backend/app/platforms/boss.py    — BossZhipinAdapter (裸 WebSocket CDP + curl_cffi)
```
每个适配器实现 `extract_price()` 和 `extract_title()`。基类负责 Playwright 生命周期管理（每次抓取 90s 超时，支持代理/CDP 模式）。

### 数据库模式
所有数据库操作用 `async with AsyncSessionLocal() as db:` 配合 `await db.commit()`。
- `backend/app/database.py` — 异步引擎、AsyncSessionLocal、get_db 依赖注入
- `backend/app/models/` — SQLAlchemy 模型：User、Product、PriceHistory、Alert、CrawlLog、JobSearchConfig、Job、JobMatch
- `backend/alembic/versions/` — 迁移文件

### 认证系统
- `POST /auth/register` — 用户注册
- `POST /auth/login` — 用户登录（JWT token，24小时有效期）
- `POST /auth/logout` — 登出
- `GET /auth/me` — 获取当前用户信息
- 密码 bcrypt 加密，登录失败锁定（5次失败锁定15分钟）
- 前端 AuthContext 状态管理，路由守卫（PublicRoute/ProtectedRoute）
- 请求拦截器自动添加 Token

### 商品抓取流程（`POST /crawl/crawl-now`）
- `_crawl_one()` 在 FastAPI async 上下文中直接运行，无 Celery 依赖
- `check_price_alerts()` 在每次抓取后对比最近两条价格记录，跌幅达标则发飞书通知
- `POST /crawl/cleanup` 手动触发旧数据清理

### Boss 职位抓取流程（`POST /jobs/crawl-now`）
- `BossZhipinAdapter.crawl()` 通过 curl_cffi 调 Boss 搜索 API，不依赖 Playwright 浏览器
- **Cookie 获取**：不做搜索 API 测试（避免消耗 token），CDP 优先 → 磁盘缓存 → 后台 tab 刷新
- **Token 刷新**：搜索和详情遇 code=37/36 自动开后台 tab 到搜索页刷新 `__zp_stoken__`（~3s），然后重试
- **Cookie 设置**：必须用 `session.cookies.set(k,v,domain=".zhipin.com")`，`update()` 不带 domain 会导致新旧 token 共存
- **详情重试**：`crawl_detail` 优先用 session 已有 cookie（来自搜索 API Set-Cookie 链），失败后才从 CDP 刷新
- **连续失败熔断**：`process_job_results` 中连续 3 次 cookie 失败自动跳过剩余详情获取
- **Adapter 共享**：`crawl_all_job_searches()` 所有 config 共享一个 adapter 实例，详情串行 2-5s 间隔

### 职位匹配分析（Job Match）
- `POST /jobs/analyze` — 对职位进行 LLM 匹配分析
- `POST /jobs/batch-analyze` — 批量并发分析（asyncio.gather batch=3）
- 支持多 LLM provider：Anthropic、OpenAI、Ollama
- 匹配结果记录到 `job_match` 表，高分职位发送飞书通知

### CDP 模式
连接已登录浏览器（`--remote-debugging-port=9222`），复用登录态绕过反爬：
```
CDP_ENABLED=true
CDP_URL=http://127.0.0.1:9222
```

## 关键约束
- user_id 硬编码为 1（单用户系统）⚠️ 已添加多用户认证，原有 user_id=1 硬编码仍适用于商品/职位爬取
- 所有时间戳字段使用 UTC 时区（`datetime.now(timezone.utc)`）
- 价格比较使用 Decimal 避免浮点误差
- LLM provider 通过 `LLMProviderFactory` 切换，支持 Anthropic/OpenAI/Ollama
