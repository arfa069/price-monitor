# 价格趋势图实现计划

基于设计文档: `docs/superpowers/specs/2026-04-24-price-trend-chart-design.md`

## 步骤 1: 安装依赖

```bash
cd frontend && npm install recharts
```

验证: `grep recharts package.json`

## 步骤 2: 创建 PriceTrendModal 组件

新建 `frontend/src/components/PriceTrendModal.tsx`:

- Props: `{ open, product, onCancel }`
- 使用 Ant Design Modal 包装
- 内部状态: `timeRange` (默认30), `historyData`, `loading`, `error`
- 时间范围按钮组: 7天/30天/90天/全部
- 统计卡片: 最低价、最高价、当前价、降价次数
- Recharts LineChart 展示价格走势
- Table 展示最近记录

## 步骤 3: 修改 ProductsPage

文件: `frontend/src/pages/ProductsPage.tsx`

- 添加 state: `trendModal: { open: boolean, product?: Product }`
- columns 操作列添加「查看趋势」按钮 (LineChartOutlined 图标)
- 导入并渲染 PriceTrendModal

## 步骤 4: 验证

1. 启动前端: `cd frontend && npm run dev`
2. 打开 http://localhost:5173
3. 点击任意商品的「查看趋势」按钮
4. 验证: 时间范围切换、图表渲染、统计卡片、表格

## 文件变更

| 文件 | 操作 |
|------|------|
| `frontend/package.json` | 添加 recharts 依赖 |
| `frontend/src/components/PriceTrendModal.tsx` | 新建 |
| `frontend/src/pages/ProductsPage.tsx` | 修改 |
