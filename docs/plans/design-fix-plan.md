# 设计修复计划

基于 design-review 发现的问题，制定以下修复计划。

## 背景

价格监控系统前端使用 Ant Design + React，目前存在以下设计问题：
- 移动端布局崩坏
- 页面缺少语义化标题
- Logo 无品牌标识
- 操作按钮间距过密

## 目标

修复 4 个高/中等影响的设计问题，提升用户体验。

---

## Task 1: 修复移动端侧边栏布局

**问题描述:**
Sidebar 使用 `position: fixed` + 固定宽度，在移动端会遮挡主内容。

**修复方案:**
在 `AppLayout.tsx` 中：
1. 添加媒体查询，窗口宽度 < 768px 时隐藏 Sidebar
2. 使用 Ant Design Drawer 作为移动端导航
3. 汉堡菜单按钮始终可见

**修改文件:**
- `frontend/src/components/AppLayout.tsx`

**验收标准:**
- [ ] 移动端 (375px) 侧边栏隐藏，显示汉堡菜单
- [ ] 点击汉堡菜单打开 Drawer 导航
- [ ] 平板/桌面端保持原有布局

---

## Task 2: 添加页面语义化标题

**问题描述:**
所有页面都没有 `<h1>` 标签，用户无法快速定位当前功能区。

**修复方案:**
在每个页面添加 `<h1>` 标题：
- `/jobs` 页面: `<h1>职位管理</h1>`
- `/products` 页面: `<h1>商品管理</h1>`
- `/schedule` 页面: `<h1>定时配置</h1>`

**修改文件:**
- `frontend/src/pages/JobsPage.tsx`
- `frontend/src/pages/ProductsPage.tsx`
- `frontend/src/pages/ScheduleConfigPage.tsx`

**验收标准:**
- [ ] 每个页面有且只有一个 h1
- [ ] h1 样式与 Ant Design 风格协调（字号约 24px，颜色 #1f2937）
- [ ] h1 在页面加载后立即可见

---

## Task 3: 添加品牌 Logo

**问题描述:**
Header 只显示文字"价格监控系统"，没有视觉品牌元素。

**修复方案:**
在 `AppLayout.tsx` Header 中：
1. 在标题左侧添加 SVG 图标（使用 price/监控相关的简单图形）
2. 或使用首字母 "价" 配合渐变背景

**修改文件:**
- `frontend/src/components/AppLayout.tsx`
- `frontend/public/favicon.svg` (如需更新)

**验收标准:**
- [ ] Logo 清晰可见，与文字标题组合协调
- [ ] 深色背景上 Logo 颜色适配
- [ ] favicon 也使用相同图标保持一致

---

## Task 4: 调整操作按钮间距

**问题描述:**
`<Space size={4}>` 间距太小，按钮过于拥挤。

**修复方案:**
在 `JobsPage.tsx` 和 `ProductsPage.tsx` 中：
- 将 `<Space size={4}>` 改为 `<Space size={8}>` 或 `<Space size="small">`

**修改文件:**
- `frontend/src/pages/JobsPage.tsx`
- `frontend/src/pages/ProductsPage.tsx`

**验收标准:**
- [ ] 按钮之间有足够间距 (8-12px)
- [ ] 操作按钮组视觉上更宽松易读
- [ ] 移动端不会因间距过大导致换行混乱

---

## Task 5: 修复 Console 弃用警告

**问题描述:**
`[antd: InputNumber] addonAfter is deprecated`

**修复方案:**
将 `addonAfter` 替换为 `Space.Compact` 包裹方式。

**修改文件:**
- `frontend/src/components/JobConfigForm.tsx` (或相关使用 InputNumber 的组件)

**验收标准:**
- [ ] Console 无弃用警告
- [ ] InputNumber 功能保持不变

---

## 执行顺序

1. Task 5 (最快，警告修复)
2. Task 2 (页面标题，简单)
3. Task 4 (按钮间距，简单)
4. Task 1 (移动端布局，复杂)
5. Task 3 (Logo 设计，可选)

## 风险

- Task 1 涉及响应式布局，可能影响桌面端布局，需仔细测试
- Task 3 Logo 设计需用户确认风格偏好
