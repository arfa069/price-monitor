# alembic/ — 数据库迁移

Alembic 迁移文件，用于异步 SQLAlchemy。

## 结构

```
alembic/
├── env.py              # 异步 SQLAlchemy 迁移环境
├── alembic.ini
└── versions/           # 迁移脚本（带时间戳）
```

## 命令

```powershell
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 运行迁移
alembic upgrade head

# 显示当前版本
alembic current
```

## 模式

- `env.py` 使用 `async_engine`（来自 `app.database`）
- 所有模型在 `env.py` 中导入，确保 autogenerate 正常工作
- 每个迁移文件：`versions/` 下的 `*.py` 文件