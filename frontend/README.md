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
├── components/     # 可复用组件（AppLayout, ProductFormModal, BatchImportModal, JobList, JobDrawer, ConfigList）
├── hooks/          # React Query hooks
├── pages/          # 页面组件（ProductsPage, ScheduleConfigPage, JobsPage）
├── types/          # TypeScript 类型定义
├── App.tsx         # 路由与布局
└── main.tsx        # 入口，QueryClientProvider
```

## 功能

- **商品管理页**: CRUD 操作、批量导入/删除/启停、分页（15条/页）、多条件筛选
- **职位管理页**: 搜索配置管理、职位列表（含可点击链接跳转Boss详情页）、单配置/全量爬取
- **定时配置页**: 爬取频率配置（直接调 PATCH /config）、Cron 表达式校验
- **告警管理**: 商品级别价格告警设置，在编辑弹窗内集成
- **爬取日志面板**: 实时查看爬取状态和历史记录
- **无障碍支持**: WCAG 合规（键盘导航、aria 属性、减少动画偏好）
- **移动端适配**: 侧边栏在移动端自动变为 Drawer 抽屉
