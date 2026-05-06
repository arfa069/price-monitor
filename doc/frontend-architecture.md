# 前端架构文档

## 1. 技术栈概览

| 层级 | 技术选型 |
|------|----------|
| 语言 | TypeScript |
| 构建工具 | Vite |
| UI 框架 | React 18 + Ant Design 5 |
| 路由 | React Router DOM v6 |
| 状态管理 | React Context（AuthContext）+ TanStack React Query |
| HTTP 客户端 | Axios |
| CSS | Ant Design token + 内联样式 |

## 2. 项目结构

```
frontend/src/
├── api/                      # API 封装层
│   ├── client.ts            # Axios 实例（拦截器 + 错误处理）
│   ├── auth.ts              # 认证 API
│   ├── products.ts          # 商品 API
│   ├── alerts.ts            # 告警 API
│   ├── crawl.ts             # 爬取 API
│   ├── config.ts            # 配置 API
│   ├── jobs.ts              # 职位 API
│   └── job_match.ts         # 匹配分析 API
├── components/              # 可复用组件
│   ├── AppLayout.tsx        # 布局组件（Header + Sidebar + Footer）
│   ├── BatchImportModal.tsx # 批量导入弹窗
│   ├── ProductFormModal.tsx # 商品表单弹窗
│   ├── PriceTrendModal.tsx  # 价格趋势弹窗
│   ├── JobConfigList.tsx    # 职位搜索配置列表
│   ├── JobConfigForm.tsx    # 职位搜索配置表单
│   ├── JobList.tsx          # 职位列表
│   ├── JobDrawer.tsx         # 职位详情抽屉
│   ├── MatchResultList.tsx  # 匹配结果列表
│   └── ResumeManager.tsx    # 简历管理器
├── contexts/
│   └── AuthContext.tsx      # 认证上下文（用户状态 + Token 管理）
├── hooks/
│   └── api.ts               # React Query hooks（所有业务数据获取）
├── pages/
│   ├── Login.tsx            # 登录页
│   ├── Register.tsx         # 注册页
│   ├── ProductsPage.tsx     # 商品管理页
│   ├── JobsPage.tsx         # 职位管理页
│   └── ScheduleConfigPage.tsx # 定时配置页
├── types/
│   └── index.ts             # TypeScript 类型定义
├── App.tsx                  # 根组件 + 路由配置
├── main.tsx                 # 入口文件
└── index.css                # 全局样式
```

## 3. 入口与路由（App.tsx）

根组件结构：

```tsx
<AuthProvider>          {/* 全局认证上下文 */}
  <QueryClientProvider> {/* 全局 React Query */}
    <ConfigProvider>    {/* Ant Design 主题配置 */}
      <BrowserRouter>
        <Routes>
          <PublicRoute>  <LoginPage />      </PublicRoute>
          <PublicRoute>  <RegisterPage />   </PublicRoute>
          <ProtectedRoute>
            <AppLayout>  <JobsPage />       </AppLayout>
          </ProtectedRoute>
          <ProtectedRoute>
            <AppLayout>  <ProductsPage />  </AppLayout>
          </ProtectedRoute>
          <ProtectedRoute>
            <AppLayout>  <ScheduleConfigPage /> </AppLayout>
          </ProtectedRoute>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  </QueryClientProvider>
</AuthProvider>
```

**路由守卫：**
- `ProtectedRoute` — 未登录重定向到 `/login`，登录后自动跳转首页
- `PublicRoute` — 已登录用户访问自动跳转 `/jobs`
- 根路径 `/` 和未知路径 `*` 重定向到 `/jobs`

**Ant Design 主题配置：**
- 主色：`#2563eb`（蓝色）
- 背景色：`#f1f5f9`
- 圆角：8px
- 字体大小：14px

## 4. 状态管理

### 4.1 认证状态（AuthContext.tsx）

```tsx
interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
}
```

**持久化策略**：Token 和用户信息存储在 `localStorage`，初始化时通过 `/auth/me` 验证 Token 有效性。

**登出流程**：
1. 清除 `localStorage` 中的 Token 和用户数据
2. 重置 `user` 状态
3. 跳转到 `/login`

### 4.2 服务端状态（React Query）

所有业务数据通过 `hooks/api.ts` 中的 hooks 管理和缓存：

| Hook | 用途 | 缓存策略 |
|------|------|----------|
| `useProducts()` | 商品列表 + 分页 | `staleTime: 10s` |
| `useJobs()` | 职位列表 + 分页 | `staleTime: 30s` |
| `useJobConfigs()` | 职位搜索配置列表 | 无持久化 |
| `useMatchResults()` | LLM 匹配结果 | 无持久化 |
| `useCrawlLogs()` | 爬取日志 | `refetchInterval: 60s` |
| `useResumes()` | 用户简历列表 | 无持久化 |
| `useConfig()` | 用户配置 | 无持久化 |

**Mutation 后自动失效**：`useMutation` 的 `onSuccess` 回调中调用 `qc.invalidateQueries` 刷新相关缓存。

## 5. API 封装层

### 5.1 Axios 实例（api/client.ts）

```ts
const api = axios.create({
  baseURL: '/api',       // Vite 代理到后端 /api 前缀
  timeout: 300000,       // 5 分钟超时（爬取操作耗时长）
})
```

**请求拦截器**：自动在 `Authorization` header 添加 `Bearer {token}`。

**响应拦截器**：
- `401` — 清除 Token，重定向到 `/login`
- `>= 500` — 全局错误提示（notification.error）
- `>= 400` — 从 `response.data.detail` 提取错误信息
- `ECONNABORTED` / 无响应 — 超时提示（notification.warning）

### 5.2 API 模块（api/*.ts）

每个域一个文件，导出命名函数：

```ts
export const productsApi = {
  list: (params) => api.get<ProductListResponse>('/products', { params }),
  create: (data) => api.post<Product>('/products', data),
  // ...
}
```

**Vite 代理配置**（vite.config.ts）：
```ts
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      rewrite: (path) => path.replace(/^\/api/, ''),  // 去掉 /api 前缀
    },
  },
}
```

## 6. 页面架构

### 6.1 商品管理页（ProductsPage.tsx）

**功能模块：**
- 商品列表（Table）：支持平台/状态/关键词筛选，分页，批量选择
- 新增/编辑商品（ProductFormModal）：表单 + 告警设置
- 批量导入（BatchImportModal）：Excel/CSV 格式解析
- 批量操作：删除、启用、停用
- 手动爬取：触发 `POST /crawl/crawl-now`，轮询任务状态
- 价格趋势（PriceTrendModal）：展示 `GET /products/{id}/history`
- 爬取日志：最近 10 条记录（60s 自动刷新）
- **翻页自动回退**：批量删除后若当前页为空，自动回退到上一页

**状态管理模式：** 组件内 `useState` 管理 UI 状态，React Query 管理服务端数据。

### 6.2 职位管理页（JobsPage.tsx）

**Tab 结构：**
- `configs` Tab：搜索配置列表 + 职位列表
- `resume` Tab：简历管理器
- `matches` Tab：匹配结果列表

**核心功能：**
- 搜索配置 CRUD + 手动触发爬取
- 职位列表：关键词/公司在客户端筛选，分页
- 匹配分数展示：`MatchResultList` 中取最高分
- 详情抽屉（JobDrawer）：展示职位完整信息

### 6.3 定时配置页（ScheduleConfigPage.tsx）

**两个表格：**
- 商品抓取定时：per-platform Cron 配置（淘宝/京东/亚马逊）
- 职位抓取定时：per-config Cron 配置

**功能：**
- Cron 表达式输入 + 实时格式校验（5 段 crontab）
- 下次执行时间展示（来自 `/products/cron-schedules` 和 `/jobs/scheduler/job-configs`）
- 飞书 Webhook URL 配置
- 数据保留天数配置

### 6.4 登录/注册页（Login.tsx / Register.tsx）

- 公开路由，用户名 + 密码表单
- 注册/登录成功后调用 `login(token, userData)` 写入 AuthContext
- 登录失败显示错误信息

## 7. 组件设计

### 7.1 AppLayout（布局组件）

**桌面端：**
- Header（固定顶部，深色背景）：Logo + 刷新按钮 + 用户下拉菜单
- Sider（固定左侧，可折叠）：导航菜单
- Content（中间区域）：页面内容
- Footer（固定底部）：版本信息

**移动端（< 768px）：**
- 汉堡菜单触发侧边 Drawer 替代 Sider
- Content 区域宽度 100%，无圆角/阴影

**导航菜单：**
- `/jobs` — 职位管理（TeamOutlined）
- `/products` — 商品管理（ShoppingCartOutlined）
- `/schedule` — 定时配置（ScheduleOutlined）

### 7.2 业务组件

| 组件 | 类型 | 说明 |
|------|------|------|
| `ProductFormModal` | 弹窗 | 新增/编辑商品，支持告警配置 |
| `BatchImportModal` | 弹窗 | 批量导入，URL 去重检测 |
| `PriceTrendModal` | 弹窗 | 价格历史折线图展示 |
| `JobConfigList` | 列表 | 搜索配置列表 + 爬取触发 |
| `JobConfigForm` | 表单 | 新增/编辑搜索配置 |
| `JobList` | 列表 | 职位列表 + 筛选 + 分页 |
| `JobDrawer` | 抽屉 | 职位详情（侧滑展示）|
| `MatchResultList` | 列表 | 匹配结果 + 分数筛选 |
| `ResumeManager` | 管理器 | 简历 CRUD |

## 8. 类型定义（types/index.ts）

所有接口类型按域划分：

```ts
// 商品域
Product, ProductListResponse, ProductCreateRequest, ProductUpdateRequest,
ProductPlatformCron, ProductPlatformCronSchedule, PriceHistoryRecord,
BatchImportRow, BatchCreateItem, BatchOperationResult,

// 告警域
Alert, AlertCreateRequest, AlertUpdateRequest,

// 爬取域
CrawlLog,

// 职位域
JobSearchConfig, JobSearchConfigCreate, JobSearchConfigUpdate,
Job, JobListResponse, JobCrawlResult,
JobConfigScheduleInfo, JobConfigCronUpdate,

// 匹配域
UserResume, UserResumeCreateRequest, UserResumeUpdateRequest,
MatchResultWithJob, MatchResultListResponse,
MatchAnalyzeRequest, MatchAnalyzeResponse,

// 配置域
UserConfig, SchedulerStatusResponse, SchedulerJobStatus,

// 认证域（单独在 auth.ts 中）
User
```

## 9. 关键交互模式

### 9.1 爬取任务轮询

手动爬取采用后台轮询模式：

```ts
// useCrawlNow 中实现
const response = await crawlApi.crawlNow()
const taskId = response.data.task_id
for (let attempts = 0; attempts < 60; attempts++) {
  await new Promise(resolve => setTimeout(resolve, 3000))  // 3s 间隔
  const status = await crawlApi.getStatus(taskId)
  if (status === 'completed') {
    const result = await crawlApi.getResult(taskId)
    return result
  }
}
```

职位爬取同样使用轮询（`useCrawlAllJobs`、`useCrawlSingleJob`）。

### 9.2 批量操作结果处理

批量操作返回 `BatchOperationResult[]`，展示成功/失败统计，失败项显示具体错误信息：

```ts
const successCount = results.filter(r => r.success).length
const failedItems = results.filter(r => !r.success)
message.success(`${action}: ${successCount} 项成功`)
if (failedItems.length > 0) {
  notification.error({ message: `${failedItems.length} 项失败`, description: ... })
}
```

### 9.3 分页自动回退

批量删除后若当前页为空，自动回退到上一页：

```ts
const shouldGoPrev = page > 1 && productItems.length === 1
deleteMutation.mutate(id, {
  onSuccess: () => {
    if (shouldGoPrev) setPage(p => Math.max(1, p - 1))
  }
})
```

## 10. 移动端响应式适配

**断点：** `MOBILE_BREAKPOINT = 768px`

| 桌面端 | 移动端 |
|--------|--------|
| 固定 Sider | 汉堡菜单 + Drawer |
| 刷新按钮在 Header | 刷新按钮在 Drawer 内 |
| Content 有圆角/阴影 | Content 无圆角/阴影 |
| Sider 宽度 180px（折叠 60px）| Drawer 宽度 220px |

## 11. 启动命令

```bash
# 安装依赖
cd frontend && npm install

# 开发环境
npm run dev          # 启动 Vite Dev Server（端口 3000）

# 生产构建
npm run build
npm run preview      # 预览构建结果
```
