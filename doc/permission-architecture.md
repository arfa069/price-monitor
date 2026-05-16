# 权限架构

> 最后更新：2026-05-11（permission-fixes plan 完成时）

## 概览

价格监控系统使用三层权限模型：**认证 → 角色 → 细粒度权限**，加上**审计日志**作为可追溯性保障。所有授权决策最终由 `app/core/permissions.py` 中的 `PERMISSIONS` 字典作为单一真相来源。

## 角色

| 角色 | 标识 | 用途 |
|------|------|------|
| 普通用户 | `user` | 默认注册角色，可操作自己的商品/职位/爬取 |
| 管理员 | `admin` | 用户管理、审计日志查看；不能执行爬取 |
| 超级管理员 | `super_admin` | 全部权限，包括调度配置 |

## 权限矩阵

来源：[`backend/app/core/permissions.py`](../backend/app/core/permissions.py)

| 权限 | user | admin | super_admin |
|------|:----:|:-----:|:-----------:|
| `user:read` | ❌ | ✅ | ✅ |
| `user:manage` | ❌ | ✅ | ✅ |
| `user:delete` | ❌ | ✅ | ✅ |
| `crawl:execute` | ✅ | ❌ | ✅ |
| `crawl:read_logs` | ✅ | ✅ | ✅ |
| `schedule:read` | ✅ | ✅ | ✅ |
| `schedule:configure` | ❌ | ❌ | ✅ |
| `config:read` | ❌ | ✅ | ✅ |
| `config:write` | ✅ | ✅ | ✅ |

## 端点 → 权限映射

### 认证 (auth.py)

| 端点 | 依赖 |
|---|---|
| `POST /auth/register` | 公开 |
| `POST /auth/login` | 公开（5 次失败锁 15 分钟） |
| `POST /auth/logout` | `get_current_user` |
| `GET /auth/me` | `get_current_user` |
| `GET /auth/sessions` | `get_current_user` |

### 用户管理 (admin.py)

| 端点 | 权限 |
|---|---|
| `GET /admin/users` | `user:read` |
| `POST /admin/users` | `user:manage` |
| `GET /admin/users/{id}` | `user:read` |
| `PATCH /admin/users/{id}` | `user:manage` |
| `DELETE /admin/users/{id}` | `user:delete` |
| `GET /admin/audit-logs` | `user:read` |
| `POST /admin/resource-permissions` | `user:manage` |
| `GET /admin/resource-permissions` | `user:read` |
| `PATCH /admin/resource-permissions/{id}` | `user:manage` |
| `DELETE /admin/resource-permissions/{id}` | `user:manage` |

### 商品 (products.py)

| 端点 | 权限 |
|---|---|
| 商品 CRUD（增删改查） | `get_current_user` |
| `POST /products/cron-configs` | `schedule:configure` |
| `PATCH /products/cron-configs/{platform}` | `schedule:configure` |
| `DELETE /products/cron-configs/{platform}` | `schedule:configure` |

### 职位 (jobs.py)

| 端点 | 权限 |
|---|---|
| 职位/简历/匹配 CRUD | `get_current_user` |
| `POST /jobs/crawl-now` | `crawl:execute` |
| `POST /jobs/crawl-now/{config_id}` | `crawl:execute` |
| `PATCH /jobs/configs/{id}/cron` | `schedule:configure` |

### 爬取 (crawl.py)

| 端点 | 权限 |
|---|---|
| `POST /crawl/crawl-now` | `crawl:execute` |
| `POST /crawl/cleanup` | `crawl:execute` |
| `GET /crawl/logs` 等 | `get_current_user` |

### 配置 (config.py)

| 端点 | 权限 |
|---|---|
| `GET /config` | `config:read` |
| `POST /config` | `config:write` |
| `PATCH /config` | `config:write` |

### 系统 (main.py)

| 端点 | 权限 |
|---|---|
| `GET /health` | 公开（仅返回 status） |
| `GET /scheduler/status` | `require_role("admin", "super_admin")` |

## Token 策略

- **算法**: HS256
- **过期**: 60 分钟（常量 `ACCESS_TOKEN_EXPIRE_MINUTES`，登录接口复用此常量）
- **登录失败**: 5 次失败锁 15 分钟（Redis 计数）
- **会话上限**: 每用户最多 5 个活跃 session
- **软删除即时失效**: `get_current_user` 检查 `deleted_at IS NULL`

## 角色边界保护

`admin` 角色不能：
- 创建 `super_admin` 用户
- 修改 `super_admin` 用户
- 删除 `super_admin` 用户

`super_admin` 不能：
- 删除自己
- 删除/禁用最后一个活跃的 `super_admin`

## 审计日志

`users_audit_logs` 表记录所有敏感操作。敏感字段（password / token / webhook_url）会被替换为 `***REDACTED***`。

记录的操作：
- `user.register`, `user.create`, `user.update`, `user.delete`
- `auth.login`, `auth.logout`, `user.password_change`

仅 `user:read` 权限可查询审计日志。

## 前端路由守卫

| 守卫 | 保护范围 | 行为 |
|---|---|---|
| `ProtectedRoute` | `/jobs`, `/products`, `/schedule`, `/profile`, `/settings` | 未登录 → `/login` |
| `AdminRoute` | `/admin/users`, `/admin/audit-logs` | 非 admin/super_admin → `/jobs` |
| `PublicRoute` | `/login`, `/register` | 已登录 → `/jobs` |

> 前端守卫仅做 UX 级别保护，**真正的安全边界在后端 API**。

## 两个授权 helper 的分工

| Helper | 来源 | 适用场景 |
|---|---|---|
| `require_permission(name)` | `app/core/permissions.py` | 业务端点（用户/爬取/调度/审计/配置） |
| `require_role(*roles)` | `app/core/security.py` | 运维型端点（如 `/scheduler/status`）—— 不需要新增权限位 |

新业务端点优先使用 `require_permission` 并维护 `PERMISSIONS` 字典；`require_role` 仅在不希望污染权限矩阵的纯运维场景使用。
