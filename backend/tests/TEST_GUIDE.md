# 测试文档

## 测试类型

| 类型 | 执行方式 | 依赖 | 覆盖范围 |
|------|----------|------|----------|
| **pytest 单元/集成测试** | `pytest -v --tb=short` | 无需真实后端（ASGITransport） | API 逻辑、schema 验证、分页计算、权限与审计回归 |
| **真实环境测试** | 启动后端后用 curl/浏览器 | PostgreSQL + Redis + uvicorn | CRUD 持久化、批量操作、UI 验证 |

---

## 阶段一：pytest 自动测试

### 运行方式

```powershell
cd C:\Users\arfac\price-monitor

# 安装测试依赖（如果缺失）
pip install pytest pytest-asyncio httpx

# 运行全量测试（与 CI 保持一致）
pytest -v --tb=short
```

### 测试文件

- `tests/` 下全部 `test_*.py` 文件（默认发现规则）
- 重点新增：`tests/test_audit_best_effort.py`（审计日志 best-effort 语义回归）

### 预期结果

```
根据当前代码基线，测试数量会增长；
核心标准是：无失败（`0 failed`）。
```

---

## 阶段二：真实环境测试

> 注意：pytest-asyncio 与 SQLAlchemy async 存在事件循环兼容性问题，
> 真实数据库测试需要在真实后端环境执行。

### 前置条件

1. **PostgreSQL** 运行在 `localhost:5432`
2. **Redis** 运行在 `localhost:6379`
3. 数据库 `pricemonitor` 已创建并迁移

### 执行步骤

```powershell
# 1. 检查数据库状态
PGPASSWORD='Adminf8869!' psql -U postgres -d pricemonitor -c "\dt"

# 2. 确保数据库已迁移（如果需要）
alembic upgrade head

# 3. 启动后端
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 4. 新开终端，启动前端
cd frontend
npm run dev
```

### API 测试命令

```bash
# Config API
curl http://127.0.0.1:8000/config
curl -X PATCH http://127.0.0.1:8000/config -H "Content-Type: application/json" -d '{"crawl_cron":"0 10 * * *"}'

# Products API
curl http://127.0.0.1:8000/products
curl http://127.0.0.1:8000/products?page=1&size=5

# 创建商品
curl -X POST http://127.0.0.1:8000/products \
  -H "Content-Type: application/json" \
  -d '{"platform":"jd","url":"https://item.jd.com/1000001.html","title":"测试商品"}'

# 批量创建
curl -X POST http://127.0.0.1:8000/products/batch-create \
  -H "Content-Type: application/json" \
  -d '{"items":[{"platform":"jd","url":"https://item.jd.com/1.html"},{"platform":"taobao","url":"https://item.taobao.com/1.html"}]}'

# Health check
curl http://127.0.0.1:8000/health
```

### 浏览器手动测试

访问 `http://localhost:3000` 进行完整 UI 测试。

参见：`tests/manual_verification_checklist.md`

---

## 数据库连接信息

```
Host:     localhost
Port:     5432
Database: pricemonitor
User:     postgres
Password: Adminf8869!
```

---

## 测试文件说明

| 文件 | 说明 |
|------|------|
| `test_api.py` | 单元测试，使用 mock 数据库 session |
| `test_phase_c_integration.py` | 集成测试，使用 ASGITransport 直接测试 FastAPI app |
| `test_audit_best_effort.py` | 审计日志 best-effort 语义：审计失败不影响主业务成功 |
| `test_integration_realdb.py` | 预留（因 pytest-asyncio 兼容性问题暂不可用） |
| `manual_verification_checklist.md` | 浏览器手动测试清单 |
