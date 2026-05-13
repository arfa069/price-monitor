# Design System — Price Monitor

## Product Context
- **What this is:** 电商价格监控系统（支持淘宝、京东、亚马逊）+ Boss直聘职位搜索监控后台。自动抓取商品/职位信息，价格降价时通过飞书 Webhook 推送告警。
- **Who it's for:** 个人用户或小型团队，需要同时监控多个电商平台价格和职位机会的运营/采购人员。
- **Space/industry:** 电商工具 / 价格追踪 / 后台管理系统（Dashboard）
- **Project type:** Web App / Dashboard / Internal Tool
- **Tech stack:** React 18 + Vite + TypeScript + Ant Design 5

## Aesthetic Direction
- **Direction:** Brutally Minimal + Playful Accents
- **Decoration level:** Intentional
- **Mood:** 专业但不沉闷，精准但不冰冷。黑白骨架传递工具的可信度，马卡龙色块作为"呼吸间隙"增加亲和力。用户打开这个后台不会觉得压抑，但也不会觉得轻浮。
- **Memorable thing:** 一个不像后台的后台 — 数据密度和视觉愉悦感并存。

## Typography
- **Display/Hero:** General Sans — 现代几何无衬线，比 Inter 更有性格但不夸张，适合工具类产品的标题和 Hero 区域。
- **Body:** DM Sans — 温暖、清晰，小字号下可读性优秀，适合密集的正文和表单标签。
- **UI/Labels:** same as body (DM Sans)
- **Data/Tables:** Geist（tabular-nums）— 等宽数字对价格、时间、ID 的对齐至关重要。
- **Code/Tags:** JetBrains Mono — 已有资产，保留用于代码块、小标签、版权文字。
- **Loading strategy:**
  - General Sans：通过 Fontshare CDN (`https://api.fontshare.com/v2/css?f[]=general-sans@400,500,600,700`) 加载
  - DM Sans：Google Fonts (`https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300..700`)
  - Geist：Google Fonts (`https://fonts.googleapis.com/css2?family=Geist:wght@400..700`) 或 Vercel CDN
  - JetBrains Mono：Google Fonts
  - 使用 `font-display: swap` 避免 FOIT
- **Scale:**
  | Token | Size | Weight | Line Height | Letter Spacing | Usage |
  |-------|------|--------|-------------|----------------|-------|
  | Hero / Display XL | clamp(32px, 5vw, 48px) | 600 | 1.0 | -1.72px | 登录页品牌标题 |
  | Display | 28px | 600 | 1.1 | -0.96px | 页面大标题 |
  | Headline | 20px | 600 | 1.35 | -0.26px | 区块标题、卡片标题 |
  | Lead | 16px | 400 | 1.40 | -0.14px | 引导段落 |
  | Body | 14px | 400 | 1.45 | -0.26px | 正文、表格内容 |
  | Small | 13px | 400 | 1.45 | -0.14px | 辅助文字、元信息 |
  | Micro | 11px | 500 | 1.30 | 0.02em | 极小标签 |
  | Eyebrow / Mono | 12px | 400 | 1.30 | 0.54px | 大写标签、表头（uppercase）|

## Color
- **Approach:** Restrained base + Expressive accents
- **Primary:** `#000000` — CTA 按钮、选中态、核心文字
- **Canvas:** `#ffffff` — 页面背景
- **Surface Soft:** `#f7f7f5` — 侧边栏、表单面板、卡片底色
- **Hairline:** `#e6e6e6` — 边框、分割线
- **Muted:** `#666666` — 次要文字、禁用态
- **Accent blocks（语义化马卡龙色块）：**
  | Color | Hex | Semantic | Used For |
  |-------|-----|----------|----------|
  | Lime | `#dceeb1` | 商品/爬取 | 商品页标题色块、爬取相关操作 |
  | Cream | `#f4ecd6` | 职位/简历 | 职位页标题色块、简历管理 |
  | Mint | `#c8e6cd` | 配置/系统 | 设置页、定时配置、系统操作 |
  | Lilac | `#c5b0f4` | 用户/账户 | 注册页装饰、个人信息、用户管理 |
  | Pink | `#efd4d4` | 告警/通知 | 告警卡片、通知提示 |
  | Coral | `#f3c9b6` | 操作/批量 | 批量操作提示、导入导出 |
  | Navy | `#1f1d3d` | 深色强调 | 深色块、对比强调 |
- **Semantic:**
  | State | Hex | Usage |
  |-------|-----|-------|
  | Success | `#1ea64a` | 价格下降、爬取成功、操作成功 |
  | Warning | `#f5a623` | Cookie 过期、待处理 |
  | Error | `#e5484d` | 爬取失败、价格上升、操作错误 |
  | Info | `#3b82f6` | 提示信息、下次执行时间 |
- **Dark mode:**
  - Canvas → `#0a0a0a`
  - Surface Soft → `#141414`
  - Hairline → `#2a2a2a`
  - Muted → `#888888`
  - Primary 反转为 `#ffffff`
  - 马卡龙色块饱和度降低 15%（保持辨识度但减少眩光）：Lime `#3a4a1a`, Cream `#4a4020`, Mint `#1a3a1a`, Lilac `#3d305a`, Pink `#4a2020`, Coral `#4a2a18`

## Spacing
- **Base unit:** 4px
- **Density:** 支持三种密度模式，通过 CSS 变量切换
  - **Compact** — 数据表格、密集列表
  - **Comfortable** — 表单、卡片（默认）
  - **Spacious** — 营销页、空状态
- **Scale:**
  | Token | Value | Usage |
  |-------|-------|-------|
  | hair | 1px | 分割线 |
  | xxs | 4px | 图标间距、紧凑内边距 |
  | xs | 8px | 按钮内边距、标签间距 |
  | sm | 12px | 表单元素间距 |
  | md | 16px | 卡片内边距、段落间距 |
  | lg | 24px | 区块间距、页面边距 |
  | xl | 32px | 大区块间距 |
  | xxl | 48px | Section 间距 |
  | section | 96px | 页面级间距 |

## Layout
- **Approach:** Grid-disciplined（数据密集型后台需要严格对齐），头部色块区允许适度打破网格。
- **Grid:** 12 列，断点 `sm:640px md:768px lg:1024px xl:1280px`
- **Max content width:** 1200px（内容区），登录页无限制。
- **Border radius hierarchy:**
  | Token | Value | Usage |
  |-------|-------|-------|
  | xs | 2px | 分割线端点 |
  | sm | 6px | 小标签、徽章 |
  | md | 8px | 输入框、下拉框、导航项 |
  | lg | 24px | 卡片、色块、表格容器 |
  | xl | 32px | 大卡片、模态框 |
  | pill | 50px | 所有按钮、状态标签、筛选 Chip |
  | full | 9999px | 头像、圆形元素 |
- **Elevation:**
  | Token | Value | Usage |
  |-------|-------|-------|
  | card | `0 4px 16px rgba(0,0,0,0.06)` | 卡片、浮层面板 |
  | modal | `0 20px 60px rgba(0,0,0,0.2)` | 模态框、抽屉 |
  | nav | `0 1px 3px rgba(0,0,0,0.08)` | 顶部导航 |

## Motion
- **Approach:** Intentional + Spring — 只有帮助理解的动效，没有炫技；页面级过渡使用轻量弹性，让后台页面切换更自然。
- **Easing:**
  - Enter: `ease-out`（元素入场快速减速，感觉"到达"）
  - Exit: `ease-in`（元素退场加速离开）
  - Move: `ease-in-out`（状态切换平滑）
- **Spring:**
  | Speed | stiffness | damping | Usage |
  |-------|-----------|---------|-------|
  | fast | 400 | 25 | 快速响应，轻微回弹 |
  | normal | 300 | 20 | 页面过渡默认值，平衡自然 |
  | slow | 200 | 15 | 柔和，明显回弹 |
- **Duration scale:**
  | Token | Duration | Usage |
  |-------|----------|-------|
  | micro | 50-100ms | 按钮 hover、颜色切换 |
  | short | 150ms | 元素入场（fadeInUp）、状态切换 |
  | medium | 200ms | 页面切换、内容区淡入 |
  | long | 300ms | 表格行数据更新闪烁、模态框出现 |
- **Specific patterns:**
  - 入场：元素从下方淡入；普通元素使用 `opacity 0→1, translateY(8px)→0`，页面使用 spring `translateY(30px)→0`
  - 状态切换：按钮/卡片 hover，`opacity/transform/border-color`，100ms ease-out
  - 数据更新：表格行背景色闪烁至色块对应色 10%，300ms ease-in-out
  - 页面切换：AppLayout 内通过 Framer Motion `AnimatePresence mode="wait"` 串行切换；新页从下方轻弹进入，旧页向上滑出并淡出
  - 组件错落入场：列表和表格容器使用 `staggerChildren: 0.05`，避免逐行干扰 Ant Design Table 虚拟化和布局计算
  - 减少动画偏好：必须同时尊重 `prefers-reduced-motion` 和 Framer Motion `useReducedMotion()`
  - **绝不使用：** 滚动视差（parallax）、无限循环装饰动画、强烈弹跳或夸张过冲

## Component Tokens
- **Button:**
  - Primary: `background: #000`, `color: #fff`, `border-radius: 50px`, `padding: 10px 24px`
  - Secondary: `background: transparent`, `color: #000`, `border: 1.5px solid #e6e6e6`, `border-radius: 50px`
  - Ghost: `background: transparent`, `color: #666`
- **Input:** `background: #f7f7f5`, `border: 1px solid #e6e6e6`, `border-radius: 8px`, `padding: 10px 14px`
  - Focus: `border-color: #000`, `box-shadow: 0 0 0 3px rgba(0,0,0,0.08)`
- **Card:** `background: #fff`, `border-radius: 24px`, `border: 1px solid #e6e6e6`, `box-shadow: 0 4px 16px rgba(0,0,0,0.06)`
- **Table:** `border-radius: 24px`, `border: 1px solid #e6e6e6`, `overflow: hidden`
  - Header row: `background: #f7f7f5`
  - Row hover: `background: rgba(0,0,0,0.02)`
- **Tag/Pill:** `border-radius: 50px`, `padding: 4px 12px`, `font-size: 12px`, `font-weight: 500`

## Ant Design Integration
- **ConfigProvider token overrides:**
  ```ts
  {
    colorPrimary: '#000000',
    colorBgLayout: '#ffffff',
    colorBgContainer: '#ffffff',
    colorText: '#000000',
    colorTextSecondary: '#666666',
    colorBorder: '#e6e6e6',
    borderRadius: 50,
    fontSize: 14,
    fontFamily: "'General Sans', 'DM Sans', system-ui, sans-serif",
  }
  ```
- **Component token overrides:**
  ```ts
  {
    Button: { borderRadius: 50, controlHeight: 40 },
    Input: { borderRadius: 8, controlHeight: 40 },
    Table: { borderRadius: 24, headerBg: '#f7f7f5' },
    Card: { borderRadius: 24 },
    Tag: { borderRadius: 50 },
    Menu: { itemSelectedBg: '#000000', itemSelectedColor: '#ffffff' },
  }
  ```

## Responsive
- **Mobile breakpoint:** 768px
- **Desktop → Mobile adaptations:**
  - Sider 隐藏，汉堡菜单触发 Drawer
  - 左右分栏（登录页）→ 上下布局
  - 装饰色块在移动端隐藏
  - 表格横向滚动
  - 按钮组垂直堆叠

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-11 | Initial design system documented | Created by /design-consultation based on existing Figma Marketing Style implementation |
| 2026-05-11 | Replace Inter with General Sans + DM Sans | Inter is overused in AI-generated designs; General Sans adds modern character without sacrificing professionalism |
| 2026-05-11 | Add Geist for data tables | Tabular numbers are critical for price alignment; Geist is purpose-built for this |
| 2026-05-11 | Semantic color blocks | Each macaron block maps to a functional domain (lime=products, cream=jobs, mint=config, etc.) |
| 2026-05-11 | Add motion spec | Previously zero motion; intentional micro-interactions improve perceived quality and state comprehension |
| 2026-05-11 | Add dark mode strategy | Night usage scenario for a tool that runs 24/7; macaron blocks desaturate 15% in dark mode |
| 2026-05-13 | Adopt light spring transitions | User selected Spring style; AppLayout owns route transitions and Settings exposes speed preference |
