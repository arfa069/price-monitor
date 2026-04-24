# 爬取日志面板实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在商品列表底部添加「最近爬取记录」面板，显示最近 10 条爬取日志

**Architecture:** 前端调用 `/crawl/logs` API 获取数据，在 ProductsPage 表格下方以卡片形式展示

**Tech Stack:** React + Ant Design + React Query + TypeScript

---

## 文件结构

```
frontend/src/
├── api/
│   └── crawl.ts        # 已存在，已有 getLogs 方法
├── pages/
│   └── ProductsPage.tsx # 修改：添加爬取日志面板
```

---

## Task 1: 添加类型定义和 hooks

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/hooks/api.ts`

- [ ] **Step 1: 添加 CrawlLog 类型到 types/index.ts**

在 `types/index.ts` 末尾添加：

```typescript
export interface CrawlLog {
  id: number
  product_id: number | null
  platform: string | null
  status: string | null
  price: number | null
  currency: string | null
  timestamp: string
  error_message: string | null
}
```

- [ ] **Step 2: 添加 useCrawlLogs hook 到 hooks/api.ts**

在文件末尾添加：

```typescript
export const useCrawlLogs = (params?: { product_id?: number; hours?: number; limit?: number }) => {
  return useQuery({
    queryKey: ['crawl-logs', params],
    queryFn: () => crawlApi.getLogs(params).then((res) => res.data),
    refetchInterval: 60000, // 每分钟自动刷新
  })
}
```

- [ ] **Step 3: 添加 import（如果还没有）**

在 hooks/api.ts 顶部添加（如果没有）：
```typescript
import { crawlApi } from '@/api/crawl'
```

- [ ] **Step 4: 验证 TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/api.ts
git commit -m "feat(frontend): 添加 CrawlLog 类型和 useCrawlLogs hook"
```

---

## Task 2: 在 ProductsPage 添加爬取日志面板

**Files:**
- Modify: `frontend/src/pages/ProductsPage.tsx`

- [ ] **Step 1: 添加 imports**

添加以下 imports：
```typescript
import { Table, Card, Tag, Space, Button, Tooltip } from 'antd'
import { ReloadOutlined, HistoryOutlined } from '@ant-design/icons'
import { useCrawlLogs } from '@/hooks/api'
```

- [ ] **Step 2: 添加爬取日志数据获取**

在组件中添加：
```typescript
const { data: crawlLogs, isLoading: logsLoading, refetch: refetchLogs } = useCrawlLogs({ limit: 10 })
```

- [ ] **Step 3: 在表格下方添加日志面板**

在 `</Space>` (包裹 Table 的) 之后、`</div>`> 之前添加：

```tsx
<Card
  size="small"
  title={
    <Space>
      <HistoryOutlined />
      最近爬取记录
      {crawlLogs && (
        <span style={{ fontSize: 12, color: '#64748b' }}>
          ({crawlLogs.length} 条)
        </span>
      )}
    </Space>
  }
  extra={
    <Button
      size="small"
      icon={<ReloadOutlined />}
      onClick={() => refetchLogs()}
      loading={logsLoading}
    >
      刷新
    </Button>
  }
  style={{ marginTop: 16 }}
>
  {logsLoading && crawlLogs?.length === 0 ? (
    <div style={{ padding: 20, textAlign: 'center', color: '#64748b' }}>
      加载中...
    </div>
  ) : crawlLogs && crawlLogs.length > 0 ? (
    <Table
      size="small"
      dataSource={crawlLogs}
      rowKey="id"
      pagination={false}
      scroll={{ x: 800 }}
      columns={[
        {
          title: '时间',
          dataIndex: 'timestamp',
          width: 160,
          render: (v: string) => new Date(v).toLocaleString('zh-CN'),
        },
        {
          title: '平台',
          dataIndex: 'platform',
          width: 80,
          render: (v: string) => {
            const colors: Record<string, string> = { taobao: '#f97316', jd: '#dc2626', amazon: '#2563eb' }
            return <Tag color={colors[v] || 'default'}>{v === 'taobao' ? '淘宝' : v === 'jd' ? '京东' : v || '-'}</Tag>
          },
        },
        {
          title: '状态',
          dataIndex: 'status',
          width: 100,
          render: (v: string) => {
            const config: Record<string, { color: string; text: string }> = {
              SUCCESS: { color: 'success', text: '成功' },
              ERROR: { color: 'error', text: '失败' },
              SKIPPED: { color: 'default', text: '跳过' },
            }
            const c = config[v] || { color: 'default', text: v || '-' }
            return <Tag color={c.color}>{c.text}</Tag>
          },
        },
        {
          title: '价格',
          dataIndex: 'price',
          width: 100,
          render: (v: number, record: any) => v ? `¥${v}` : '-',
        },
        {
          title: '错误信息',
          dataIndex: 'error_message',
          ellipsis: true,
          render: (v: string) => v ? (
            <Tooltip title={v}>
              <span style={{ color: '#dc2626' }}>{v}</span>
            </Tooltip>
          ) : '-',
        },
      ]}
    />
  ) : (
    <div style={{ padding: 20, textAlign: 'center', color: '#64748b' }}>
      暂无爬取记录
    </div>
  )}
</Card>
```

- [ ] **Step 4: 验证 TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ProductsPage.tsx
git commit -m "feat(frontend): 添加爬取日志面板"
```

---

## Task 3: 整体验证

- [ ] **Step 1: 启动前端验证**

Run: `cd frontend && npm run dev`

- [ ] **Step 2: 测试日志面板显示**

打开商品管理页，验证底部「最近爬取记录」面板正确显示

- [ ] **Step 3: 测试刷新功能**

点击刷新按钮，验证日志更新

- [ ] **Step 4: 测试自动刷新**

等待 1 分钟，验证日志自动更新

---

## 验收标准

1. 商品列表底部显示「最近爬取记录」面板
2. 面板显示最近 10 条爬取日志
3. 显示时间、平台、状态、价格、错误信息
4. 有刷新按钮可手动刷新
5. 每分钟自动刷新
6. 无爬取记录时显示「暂无爬取记录」
7. TypeScript 编译通过
