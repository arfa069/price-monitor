# Header 和 Footer 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为价格监控系统添加全局 Header 和 Footer，完善页面布局结构

**Architecture:** 基于 Ant Design 6 Layout 组件实现 Header + Content + Sider + Footer 的经典管理后台布局。Header 包含品牌标识和全局操作，Footer 显示系统状态信息。

**Tech Stack:** React 19 + Ant Design 6 + TypeScript + Vite

---

## 文件结构

```
frontend/src/
├── components/
│   ├── AppLayout.tsx          # 修改：添加 Header/Footer
│   └── components/
│       ├── Header.tsx         # 新建：Header 组件（可选抽离）
│       └── Footer.tsx          # 新建：Footer 组件（可选抽离）
├── pages/
│   ├── ProductsPage.tsx
│   └── ScheduleConfigPage.tsx
├── App.tsx
└── main.tsx
```

---

## Task 1: 修改 AppLayout 添加 Header

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx:1-72`

- [ ] **Step 1: 添加 Layout.Header 导入**

修改 `frontend/src/components/AppLayout.tsx` 第9行：
```typescript
const { Sider, Content, Header, Footer } = Layout
```

- [ ] **Step 2: 添加 Header 组件**

修改 `frontend/src/components/AppLayout.tsx` 第23-72 行的 return 语句，在 `<Layout>` 后添加：

```typescript
return (
  <Layout style={{ minHeight: '100vh' }}>
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        background: '#001529',
      }}
    >
      <div
        style={{
          color: '#fff',
          fontSize: 18,
          fontWeight: 'bold',
        }}
      >
        价格监控系统
      </div>
      <div style={{ flex: 1 }} />
      <Button type="text" icon={<ReloadOutlined />} style={{ color: '#fff' }}>
        刷新
      </Button>
    </Header>
    <Layout>
      {/* 现有的 Sider 部分保持不变 */}
      ...
    </Layout>
    <Footer
      style={{
        textAlign: 'center',
        padding: '12px 24px',
        background: '#001529',
        color: '#fff',
        fontSize: 12,
      }}
    >
      价格监控系统 v1.0 · 最后更新: {new Date().toLocaleString('zh-CN')}
    </Footer>
  </Layout>
)
```

需要添加 ReloadOutlined 图标导入（第4-7行）：
```typescript
import {
  ShoppingCartOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
```

添加 Button 导入（第2行）：
```typescript
import { Layout, Menu, Button } from 'antd'
```

- [ ] **Step 3: 验证构建**

Run: `cd frontend && npm run build`
Expected: 编译成功，无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/AppLayout.tsx
git commit -m "feat(frontend): add Header and Footer to AppLayout"
```

---

## Task 2: 添加 Header 交互功能（可选增强）

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: 添加手动触发全局刷新的回调**

在 AppLayout 中添加 onRefresh 回调 props：

```typescript
export default function AppLayout({
  children,
  onRefresh
}: {
  children: React.ReactNode
  onRefresh?: () => void
}) {
  // ... 现有代码 ...
  const handleRefresh = () => {
    if (onRefresh) onRefresh()
  }
  // Button 改为 onClick={handleRefresh}
}
```

- [ ] **Step 2: 在 App.tsx 中传递刷新回调**

修改 `frontend/src/App.tsx`：

```typescript
import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export default function App() {
  const queryClient = useQueryClient()
  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries()
  }, [queryClient])

  return (
    // ...
    <AppLayout onRefresh={handleRefresh}>
    // ...
  )
}
```

需要确保 QueryClientProvider 在 App 内部：
- 检查 `frontend/src/main.tsx` 确认 QueryClientProvider 已包裹 App
- 如果是，从 App.tsx 中移除或调整

- [ ] **Step 3: 验证构建**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 4: 提交**

```bash
git add frontend/src/App.tsx frontend/src/components/AppLayout.tsx frontend/src/main.tsx
git commit -m "feat(frontend): add global refresh functionality"
```

---

## Task 3: 响应式适配（可选）

**Files:**
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: 添加移动端折叠 Sider 的默认行为**

```typescript
const [collapsed, setCollapsed] = useState(true) // 默认折叠
```

- [ ] **Step 2: 添加移动端 Header 菜单按钮**

在 Header 中添加移动端菜单切换按钮（可选）：
```typescript
import { BarsOutlined } from '@ant-design/icons'

// Header 中
{collapsed && (
  <Button
    type="text"
    icon={<BarsOutlined />}
    style={{ color: '#fff' }}
    onClick={() => setCollapsed(!collapsed)}
  />
)}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/AppLayout.tsx
git commit -m "feat(frontend): improve mobile responsive behavior"
```

---

## 验证清单

完成所有任务后验证：

- [ ] 页面包含 Header（品牌名 + 刷新按钮）
- [ ] 页面包含 Footer（版本号 + 时间戳）
- [ ] Header/Footer 在所有页面保持一致
- [ ] 移动端 Sider 默认折叠
- [ ] 刷新按钮点击后触发数据重新加载
- [ ] 样式与现有设计风格一致
- [ ] 编译无错误

---

## 替代方案

如果只需要简单实现（Task 1 即可满足需求），跳过 Task 2 和 Task 3。Header 显示品牌标识 + 当前时间，Footer 显示固定文字即可。
