# 动效实施计划：管理页面入场动画

## 背景

DESIGN.md 动效规范要求：
- 入场动画：元素从下方 8px 淡入，`opacity 0→1, translateY(8px)→0`，150ms ease-out
- 页面切换：内容区淡入，`opacity 0→1`，200ms ease-out
- 绝不使用：弹跳、弹性过冲、滚动视差

当前状态：
- Login/Register 已完整实现（7-8 处 fadeInUp 交错动画）
- 所有管理页面（ProductsPage、JobsPage、ScheduleConfigPage、Profile、Settings、AdminUsers、AdminAuditLogs）**零实现**
- AppLayout 布局组件**零实现**
- motion.css 已定义完整动画系统

---

## 方案选择

### 方案 A：在各页面组件直接添加动画类（推荐）

**做法：** 在每个管理页面组件的根元素添加 `animate-fade-in-up` 类

**优点：**
- 最小改动，与 Login/Register 保持一致
- 复用已有的 motion.css 系统
- 可精确控制每个元素的动画顺序

**缺点：**
- 需要修改多个页面文件
- 动画效果相对简单

### 方案 B：统一包装组件

**做法：** 创建 `AnimatedPage` 包装组件，统一处理动画

**优点：**
- 一处修改，全局生效
- 便于后续统一调整

**缺点：**
- 引入额外组件层级
- 与 Login/Register 不一致

### 方案 C：路由级别切换动画

**做法：** 在 React Router 配置中添加路由切换动画

**优点：**
- 页面切换体验流畅
- 一次配置，所有页面生效

**缺点：**
- 实现复杂度高
- 与设计稿风格可能不匹配

---

## 推荐方案：A

复用 Login/Register 的实现模式，在每个管理页面的根元素添加 `animate-fade-in-up` 类。

---

## 实施步骤

### Step 1: AppLayout 入场动画

在 `AppLayout.tsx` 的 `<style>` 中为顶部导航和侧边栏添加动画：

```css
/* Header 入场动画 */
.ant-layout-header {
  animation: fadeInUp 150ms ease-out forwards;
}

/* Sider 入场动画 */
.ant-layout-sider {
  animation: fadeInUp 150ms ease-out 50ms both;
}

/* Footer 入场动画 */
.ant-layout-footer {
  animation: fadeInUp 150ms ease-out 100ms both;
}
```

### Step 2: 页面入场动画

在 `components.css` 中添加页面根元素动画样式：

```css
/* 页面入场动画 */
.page-root {
  animation: fadeInUp 200ms ease-out forwards;
}

/* 页面头部色块 */
.page-header {
  animation: fadeInUp 200ms ease-out forwards;
}

/* 工具栏卡片 */
.fg-card {
  animation: fadeInUp 200ms ease-out 50ms both;
}

/* 表格 */
.ant-table-wrapper {
  animation: fadeInUp 200ms ease-out 100ms both;
}
```

### Step 3: 验证

- 访问 `/products`、 `/jobs` 等页面
- 验证入场动画是否正确触发
- 验证动画时长和缓动是否符合规范（150-200ms，ease-out）

---

## 待修改文件

| 文件 | 修改内容 |
|------|---------|
| `frontend/src/components/AppLayout.tsx` | 添加 Header/Sider/Footer 入场动画 |
| `frontend/src/styles/components.css` | 添加 `.page-root`、`.page-header`、`.fg-card` 动画 |

**不需要修改的页面文件：**
- ProductsPage、JobsPage 等无需改动，通过全局样式自动生效

---

## 验证标准

- [ ] AppLayout 导航加载时有淡入动画
- [ ] 管理页面内容加载时有淡入动画
- [ ] 动画时长 150-200ms
- [ ] 动画缓动为 ease-out
- [ ] 无页面出现跳动或闪烁