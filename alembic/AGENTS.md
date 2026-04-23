# alembic/ — 数据库迁移

Alembic 迁移目录，负责维护 PostgreSQL 模式变更。

## 结构

```text
alembic/
├── env.py              # Alembic 环境（异步 SQLAlchemy）
├── script.py.mako      # 迁移模板
└── versions/           # 迁移脚本（时间戳命名）
```

## 常用命令

```powershell
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 查看当前版本
alembic current
```

## 约定

- `env.py` 需导入 `app.models` 元数据，保证 `--autogenerate` 可识别模型变更。
- 新增/修改以下核心表时，必须配套迁移：`users`、`products`、`price_history`、`alerts`、`crawl_logs`。
- 迁移脚本应可重复执行且可回滚；避免在迁移中写入与环境强耦合的逻辑。

## 与系统架构关系

- 该项目抓取在 FastAPI 进程内执行，不依赖 Celery worker。
- Alembic 仅负责数据库结构演进，不承担任务调度功能。
