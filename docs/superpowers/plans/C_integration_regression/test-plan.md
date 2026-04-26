# 阶段C联调与回归验收计划

## 1. 目标
- 基于阶段A+B成果，完成端到端联调、回归与边界验收。
- 产出可用于发布决策的结构化测试报告。

## 2. 执行方式

### 自动化测试（pytest）
```bash
# API 层测试：21 个用例（自动运行）
pytest tests/test_phase_c_integration.py -v

# 原有测试回归
pytest tests/test_api.py tests/test_models.py -v
```

### 手动验证（浏览器）
- 手动验证清单：`tests/manual_verification_checklist.md`
- 需要浏览器截图的用例在此清单中列出

## 3. 联调清单（端到端）
| 编号 | 场景 | 预期结果 | 自动化 | 手动 |
|---|---|---|---|---|
| C-01 | 前端默认入口 | `http://localhost:3000` 默认进入商品管理页 | — | ✓ |
| C-02 | 侧边栏常驻路由 | 点击菜单后右侧切页，左侧栏不消失 | — | ✓ |
| C-03 | 商品全流程 | 单条 CRUD + 批量新增/删除/启停可用 | ✓ CRUD | ✓ 批量 |
| C-04 | 服务端分页 | 每页 15 条，筛选与分页联动正常 | ✓ | ✓ 截图 |
| C-05 | 定时配置真实读写 | GET 展示后端值，PATCH 保存生效 | ✓ | ✓ 草稿 |
| C-06 | 调度触发 | APScheduler 按 cron 触发任务 | ✓ (mock) | ✓ 日志 |
| C-07 | 调度热更新 | 更新 cron 后无需重启即生效 | ✓ (mock) | ✓ API |
| C-08 | 手动抓取回归 | POST `/crawl/crawl-now` 正常 | ✓ | — |
| C-09 | 健康检查回归 | GET `/health` 正常 | ✓ | — |
| C-10 | 自动化测试回归 | `pytest` 全量通过 | ✓ | — |

## 4. 边界专项
| 编号 | 场景 | 预期结果 | 自动化 | 手动 |
|---|---|---|---|---|
| C-E01 | /products page 越界 | 空 `items` + 正常分页元信息 | ✓ | — |
| C-E02 | 筛选无结果 | `total=0` 且页面稳定 | ✓ | — |
| C-E03 | 批量新增重复 URL | 输入内重复去重，已存在重复有提示 | ✓ | — |
| C-E04 | 批量操作部分失败 | 成功/失败统计可见，失败原因可读 | ✓ | — |
| C-E05 | 删除后当前页空 | 自动回退上一页并刷新 | — | ✓ |
| C-E06 | 非法 cron | 后端 422，前端禁止保存并提示 | ✓ | ✓ 截图 |
| C-E07 | 配置缺失 | 提供默认配置或自动创建默认配置 | ✓ | — |
| C-E08 | 5xx/超时 | 前端可重试提示，不静默失败 | — | ✓ |
| C-E09 | 调度重叠执行 | 后触发跳过，日志明确标记 skip | ✓ | — |

## 5. 执行与记录规范
- 每条用例记录：通过/失败、环境、步骤、实际结果、证据链接。
- 证据必须包含：关键状态码、核心响应字段、关键日志片段。
- scheduler 相关必须补充：job id、cron 表达式、触发时间（Asia/Shanghai）。

## 6. 测试产出

### pytest 结果摘要（最新）
```
tests/test_phase_c_integration.py: 22 passed
tests/test_api.py: 9 passed
tests/test_models.py: 8 passed
---
Total: 39 passed
```

### 手动验证清单
- 文件：`tests/manual_verification_checklist.md`
- 需截图的用例在清单中标记

## 7. 交付判定模板
| 项目 | 内容 |
|---|---|
| 总用例数 | N |
| 通过数 | N |
| 失败数 | N |
| 阻塞数 | N |
| 发布结论 | 可发布 / 不可发布 |
| 结论理由 | 一句话总结 |

### 缺陷分级建议
- P0：核心流程不可用或数据错误，阻塞发布。
- P1：主要流程受损，有明显业务风险，原则上阻塞发布。
- P2：存在可接受绕过方案，不阻塞但需排期修复。
- P3：体验或文案问题，不影响主要功能。

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 2 | clean | mode: HOLD_SCOPE, 1 critical gaps |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 5 | CLEAR | 2 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | clean | score: 7/10 → 9/10, 2 decisions |

- **UNRESOLVED:** 0
- **VERDICT:** CEO + ENG + DESIGN CLEARED — ready to ship

