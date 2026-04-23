# 价格监控系统前端

React + Vite + TypeScript + Ant Design 前端应用。

## 安装

```bash
npm install
```

## 开发

```bash
# 确保后端运行在 http://127.0.0.1:8000
npm run dev
```

前端运行在 http://localhost:3000，自动代理 `/api` 请求到后端。

## 构建

```bash
npm run build
```

产物输出到 `dist/` 目录。

## 目录结构

```
src/
├── api/            # axios 实例与 API 函数
├── components/     # 可复用组件（AppLayout, ProductFormModal, BatchImportModal）
├── hooks/          # React Query hooks
├── pages/          # 页面组件（ProductsPage, ScheduleConfigPage）
├── types/          # TypeScript 类型定义
├── App.tsx         # 路由与布局
└── main.tsx        # 入口，QueryClientProvider
```

## 功能

- **商品管理页**: CRUD 操作、批量导入/删除/启停、分页（15条/页）、多条件筛选
- **定时配置页**: 爬取频率配置（直接调 PATCH /config）、Cron 表达式校验（localStorage 占位）
