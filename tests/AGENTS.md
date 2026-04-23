# tests/ — 测试套件

项目使用 `pytest`，覆盖 API、模型与关键业务流程。

## 结构

```text
tests/
├── conftest.py         # 测试夹具（app/client/db 会话）
├── test_api.py         # 路由与接口行为
└── test_models.py      # 模型约束与关系
```

## 常用命令

```powershell
# 全量测试
pytest

# 仅跑 API
pytest tests/test_api.py

# 仅跑模型
pytest tests/test_models.py
```

## 测试重点

- `/products`、`/alerts`、`/crawl/*`、`/health` 的响应与状态码
- 抓取后价格历史入库与降价告警触发逻辑
- 清理接口对历史数据与抓取日志的保留策略

## 架构一致性要求

- 项目抓取流程在 FastAPI 异步上下文内执行（非 Celery worker）。
- 如测试中出现 Celery 假设或依赖，应移除并改为接口/服务层异步流程验证。
