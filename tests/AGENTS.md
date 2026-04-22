# tests/ — 测试套件

pytest 测试，`asyncio_mode = auto`。测试结构与 `app/` 对应。

## 结构

```
tests/
├── conftest.py         # 夹具（app, client, db）
├── test_api.py
└── test_models.py
```

## 命令

```powershell
pytest
pytest tests/test_api.py
```