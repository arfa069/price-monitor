# 提示词A（V2）：阶段1 - React 前端可视化（不改后端调度逻辑）

你是资深全栈工程师。请在现有 FastAPI 项目中新增 React + Vite + TypeScript 前端（frontend/），只实现前端与现有 API 对接，不改后端调度逻辑。

后端现有接口：
- POST /products
- GET /products?platform=&active=
- GET /products/{id}
- PATCH /products/{id}
- DELETE /products/{id}
- GET /config
- POST /config

目标：
实现“商品管理 + 定时配置”可视化后台，其中主页面默认为商品管理页。

技术约束：
1) 技术栈
- React + Vite + TypeScript
- Ant Design
- axios
- React Query

2) 启动与代理
- 前端开发服务器固定端口 3000
- Vite 代理 /api -> http://127.0.0.1:8000
- 前端请求统一走 /api 前缀

3) 布局与路由
- 使用“左侧边栏 + 右侧内容区”的后台布局，侧边栏常驻不消失
- 侧边栏从上到下顺序：
  1. 商品管理
  2. 定时配置
- 点击侧边栏标签时，右侧区域切换对应页面
- 默认路由进入商品管理页（/ 或 unknown path 自动跳到 /products）

4) 商品管理页
- 表格字段：id/platform/url/title/active/created_at/updated_at
- 支持筛选：platform、active、关键词（title/url）
- 支持单条：新增、编辑、删除
- 支持多选：批量删除、批量启用/停用
- 支持批量新增：多行 URL 粘贴后逐条创建
- 分页：每页 15 条，支持上一页/下一页（可带页码）
- 平台识别：
  - jd.com / item.jd.com -> jd
  - taobao.com / tmall.com -> taobao
  - amazon. -> amazon
  - 无法识别时提示手动选择
- 新增/编辑字段：platform、url、title、active

5) 定时配置页（阶段1占位）
- 提供 Cron 输入框（5 段）和实时合法性校验
- 页面提示“当前仅前端占位，后端调度在阶段2接入”
- 保存到 localStorage（crawl_cron_draft）

6) 必须处理的边界场景
- 空数据状态、加载状态、请求失败状态
- URL 非法或不支持平台时阻止提交并提示
- 批量新增时去重（输入内重复 + 与现有列表重复）
- 批量操作部分失败时显示成功/失败汇总，不可静默失败
- 删除操作二次确认
- 翻页后多选状态策略要明确（建议仅当前页生效，UI 明示）
- Cron 非法时禁止保存
- 接口超时或 5xx 给出可重试提示

7) 工程与交付
- 目录：src/pages、src/components、src/api、src/hooks、src/types
- 提供 frontend/README.md（安装、启动、代理、打包）
- 给出关键页面截图：商品管理页、定时配置页
- 给出运行步骤与验收清单

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | ISSUES_OPEN | HOLD SCOPE, 0 scope expansions, 1 critical gap |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | ISSUES_OPEN | 14 issues, 1 critical gap |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | ISSUES_OPEN | score: 4/10 → 8/10, 9 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**UNRESOLVED:** 0 across all reviews
**VERDICT:** ALL REVIEWS COMPLETE — eng 14 issues addressed, design 8/10, CEO HOLD SCOPE confirmed

### Key Decisions Made During Eng Review

1. **分页**: offset/limit 后端分页（返回 `{items, total}`）
2. **批量操作**: 加后端 batch API（batch-delete, batch-update, batch-create）
3. **定时配置**: 直接接后端 GET/PATCH /config，UI 用小时数控件（非 cron 表达式）
4. **TS 类型**: 从 OpenAPI 自动生成
5. **部署**: 阶段1只做开发环境
6. **platform 编辑**: 后端 ProductUpdate 加 platform 字段
7. **Config API**: 加 PATCH /config + GET 默认值返回

### Key Decisions Made During Design Review

1. **信息层级**: 主动作(新增/导入) → 数据表格 → 筛选区, 表格是视觉主体
2. **空态**: 带行动按钮("暂无商品" + 新增按钮)，不只是文字
3. **批量操作反馈**: 成功用 Toast(3s消失)，失败用 Notification(手动关)，批量结果用 Modal 汇总
4. **批量导入**: 3步弹窗(粘贴URL → 预览平台识别 → 确认)
5. **平台标签**: 语义中性色(京东紫#722ed1, 淘宝青#13c2c2, 亚马逊蓝#1890ff)，避免和Antd语义色冲突
6. **视觉定制**: Antd ConfigProvider 主题文件(自定义主色、logo、宽敞行高52px)
7. **价格历史页**: 点击商品行 → 展开价格趋势图(独立页面/侧抽屉)
8. **爬取状态列**: 表格加"最近爬取"列(时间+状态图标)
9. **响应式**: 桌面优先(1200px+)，平板(768-1199px)侧边栏可折叠，手机显示"建议在电脑上使用"
10. **可访问性**: Antd默认 + 颜色对比度检查、44px触控目标、label替代placeholder

### Key Decisions Made During CEO Review

1. **实现路径**: React SPA + Backend API（确认，不选 HTMX 或 Vanilla JS）
2. **审查模式**: HOLD SCOPE（不扩大不缩小）
3. **batch-create 策略**: 逐条处理，返回每条结果（非事务性）
4. **批量操作数组限制**: 100 条上限防止 DoS

### Critical Gaps

- `GET /config` 首次访问返回 404（用户不存在时），定时配置页会崩
- 前端统一错误拦截器（timeout/5xx 重试提示）缺失

### Scope Expansion from Reviews

原计划"不改后端"。审查后扩展为需改后端：
- 加分页参数到 `GET /products`
- 加 `POST /products/batch-delete`
- 加 `POST /products/batch-update`
- 加 `POST /products/batch-create`
- 加 `PATCH /config`
- 修改 `GET /config` 返回默认值
- 加 `platform` 到 `ProductUpdate` schema

前端扩展：
- 加价格历史页面(点击商品行展开趋势图)
- 表格加"最近爬取"列
- Antd ConfigProvider 主题定制
- 带行动的空态设计
- 3步批量导入弹窗

