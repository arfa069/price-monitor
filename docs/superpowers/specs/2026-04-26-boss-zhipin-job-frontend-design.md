# Boss 直聘职位爬虫前端实现

**日期**: 2026-04-26
**状态**: 设计完成

## 概述

为 Boss 直聘职位爬虫系统实现前端管理界面，包括搜索配置管理和职位列表查看。

## 目录结构

```
frontend/src/
├── pages/JobsPage.tsx              # 主页面，组合各组件
├── components/
│   ├── JobConfigList.tsx           # 搜索配置卡片列表
│   ├── JobConfigForm.tsx           # 配置表单（新建/编辑）
│   ├── JobList.tsx                 # 职位表格
│   └── JobDrawer.tsx               # 职位详情抽屉
├── api/jobs.ts                     # 职位相关 API
├── types/job.ts                    # TypeScript 类型定义
└── hooks/useJobs.ts                # React Query hooks

后端已实现：
├── app/routers/jobs.py             # API 路由
├── app/models/job.py               # 数据模型
├── app/schemas/job.py              # Pydantic schemas
└── app/services/job_crawl.py      # 爬取服务
```

## 功能清单

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 配置管理 | 新增/编辑/删除/启用搜索配置 | P0 |
| 手动爬取 | 单个配置爬取 + 全部爬取 | P0 |
| 职位列表 | 分页/筛选/排序/搜索 | P0 |
| 职位详情 | 抽屉展示完整信息 | P0 |
| 新职位通知 | 飞书推送（后端已实现） | P1 |

## API 对应

| 前端函数 | 后端 endpoint | 说明 |
|----------|---------------|------|
| `GET /configs` | GET /jobs/configs | 列表搜索配置 |
| `POST /configs` | POST /jobs/configs | 创建搜索配置 |
| `PATCH /configs/:id` | PATCH /jobs/configs/{config_id} | 更新搜索配置 |
| `DELETE /configs/:id` | DELETE /jobs/configs/{config_id} | 删除搜索配置 |
| `GET /jobs` | GET /jobs | 列表职位（支持筛选分页） |
| `GET /jobs/:id` | GET /jobs/{job_id_str} | 职位详情 |
| `POST /crawl-now` | POST /jobs/crawl-now | 爬取所有配置 |
| `POST /crawl-now/:id` | POST /jobs/crawl-now/{config_id} | 爬取单个配置 |

## 数据模型

### JobSearchConfig（搜索配置）

```typescript
interface JobSearchConfig {
  id: number
  user_id: number
  name: string
  keyword: string | null
  city_code: string | null
  salary_min: number | null
  salary_max: number | null
  experience: string | null
  education: string | null
  url: string
  active: boolean
  notify_on_new: boolean
  created_at: string
  updated_at: string
}
```

### Job（职位）

```typescript
interface Job {
  id: number
  job_id: string          // Boss 加密 ID
  search_config_id: number
  title: string | null
  company: string | null
  company_id: string | null
  salary: string | null   // 如 "20-40K·14薪"
  salary_min: number | null
  salary_max: number | null
  location: string | null
  experience: string | null
  education: string | null
  description: string | null
  url: string | null
  first_seen_at: string
  last_updated_at: string
  is_active: boolean
}
```

## 页面布局

```
┌─────────────────────────────────────────────────────────┐
│  价格监控系统                                   [刷新]  │
├────────┬────────────────────────────────────────────────┤
│        │                                                │
│ 商品管理│  ┌─ 搜索配置 ─────────────────────────────┐  │
│        │  │ [+ 新增配置]                           │  │
│ 定时配置│  │                                        │  │
│        │  │ [配置卡片1] [配置卡片2] [配置卡片3]    │  │
│ 职位管理│  │ [编辑] [爬取] [删除]  ...             │  │
│        │  └────────────────────────────────────────┘  │
│        │                                                │
│        │  ┌─ 职位列表 ────────────────────────────┐  │
│        │  │ [全部爬取]   [搜索框...] [筛选...]    │  │
│        │  ├────────────────────────────────────────┤  │
│        │  │ 职位名│ 公司  │ 薪资 │ 地区 │ 状态 │ 操作 │  │
│        │  ├────────────────────────────────────────┤  │
│        │  │ ...                                     │  │
│        │  └────────────────────────────────────────┘  │
│        │  共 N 条  ◀ 1 2 3 ▶                        │
└────────┴────────────────────────────────────────────────┘
```

## 组件设计

### JobsPage

主页面容器，负责布局和状态提升：
- 维护筛选/搜索状态
- 组合 JobConfigList 和 JobList
- 处理配置表单的开关状态

### JobConfigList

配置卡片列表：
- 显示所有配置为卡片形式
- 每卡片显示：名称、关键词、薪资范围、URL 预览、启用状态
- 操作按钮：编辑、爬取、删除
- 新增按钮打开表单

### JobConfigForm

配置表单 Modal/Drawer：
- 字段：名称、关键词、城市代码、薪资范围(最小/最大)、经验、学历、URL、启用开关、通知开关
- URL 字段提供输入提示
- 表单验证：URL 必填，名称必填

### JobList

职位表格：
- 列：职位名、公司、薪资、地区、经验、学历、首次发现时间、状态、操作
- 支持排序：首次发现、最后更新、薪资
- 支持筛选：搜索关键词、配置、薪资范围、地区、状态
- 分页：每页 20 条
- 操作：查看详情（打开抽屉）

### JobDrawer

职位详情抽屉：
- 展示完整职位信息
- 包含：职位名、公司、薪资、地区、经验、学历、描述、发现时间、最后更新时间
- 提供跳转 Boss 详情页链接

## 实现顺序

1. **types/job.ts** - 类型定义
2. **api/jobs.ts** - API 封装
3. **hooks/useJobs.ts** - React Query hooks
4. **components/JobConfigForm.tsx** - 配置表单
5. **components/JobConfigList.tsx** - 配置列表
6. **components/JobDrawer.tsx** - 详情抽屉
7. **components/JobList.tsx** - 职位表格
8. **pages/JobsPage.tsx** - 主页面
9. **App.tsx** - 添加路由和侧边栏菜单

## 技术栈

- React 18 + TypeScript
- Ant Design 5.x
- React Router 6
- React Query (TanStack Query)
- 样式：内联样式（沿用现有模式）