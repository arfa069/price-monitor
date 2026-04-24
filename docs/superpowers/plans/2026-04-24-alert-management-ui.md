# 告警管理 UI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在商品管理页集成告警管理，用户可在商品列表查看告警状态，在编辑商品弹窗中设置/修改告警

**Architecture:** 前端单独请求 `/alerts` API 获取告警列表，与商品数据合并后展示。告警编辑集成在商品编辑弹窗中，实时保存或提交时同步

**Tech Stack:** React + Ant Design + React Query + TypeScript

---

## 文件结构

```
frontend/src/
├── api/
│   └── alerts.ts          # 新增：告警 API 调用
├── hooks/
│   └── api.ts              # 修改：添加 useAlerts, useCreateAlert, useUpdateAlert, useDeleteAlert
├── pages/
│   └── ProductsPage.tsx    # 修改：显示告警列，编辑弹窗中集成告警区块
├── components/
│   └── ProductFormModal.tsx # 修改：底部增加「价格告警设置」区块
└── types/
    └── index.ts            # 修改：添加 Alert 相关类型
```

---

## Task 1: 添加告警类型定义

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 添加 Alert 类型定义**

在 `types/index.ts` 末尾添加：

```typescript
export interface Alert {
  id: number
  product_id: number
  alert_type: string
  threshold_percent: number | null
  last_notified_at: string | null
  last_notified_price: number | null
  active: boolean
  created_at: string
  updated_at: string
}

export interface AlertCreateRequest {
  product_id: number
  threshold_percent?: number
  active?: boolean
}

export interface AlertUpdateRequest {
  threshold_percent?: number
  active?: boolean
}
```

- [ ] **Step 2: 验证 TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(frontend): 添加 Alert 类型定义"
```

---

## Task 2: 创建告警 API 模块

**Files:**
- Create: `frontend/src/api/alerts.ts`

- [ ] **Step 1: 创建 alerts.ts**

```typescript
import api from './client'
import type { Alert, AlertCreateRequest, AlertUpdateRequest } from '@/types'

export const alertsApi = {
  list: (params?: { product_id?: number; active?: boolean }) =>
    api.get<Alert[]>('/alerts', { params }),

  get: (id: number) =>
    api.get<Alert>(`/alerts/${id}`),

  create: (data: AlertCreateRequest) =>
    api.post<Alert>('/alerts', data),

  update: (id: number, data: AlertUpdateRequest) =>
    api.patch<Alert>(`/alerts/${id}`, data),

  delete: (id: number) =>
    api.delete(`/alerts/${id}`),
}
```

- [ ] **Step 2: 验证 TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/alerts.ts
git commit -m "feat(frontend): 添加告警 API 模块"
```

---

## Task 3: 添加告警相关 hooks

**Files:**
- Modify: `frontend/src/hooks/api.ts`

- [ ] **Step 1: 添加 import**

在文件顶部添加：
```typescript
import { alertsApi } from '@/api/alerts'
import type { AlertUpdateRequest } from '@/types'
```

- [ ] **Step 2: 在文件末尾添加 hooks**

```typescript
export const useAlerts = (productId?: number) => {
  return useQuery({
    queryKey: ['alerts', productId],
    queryFn: () => alertsApi.list(productId !== undefined ? { product_id: productId } : undefined).then((res) => res.data),
    enabled: productId !== undefined,
  })
}

export const useCreateAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: alertsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export const useUpdateAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlertUpdateRequest }) =>
      alertsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export const useDeleteAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: alertsApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}
```

- [ ] **Step 3: 验证 TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/api.ts
git commit -m "feat(frontend): 添加告警管理 hooks"
```

---

## Task 4: 在商品列表显示告警列

**Files:**
- Modify: `frontend/src/pages/ProductsPage.tsx`

- [ ] **Step 1: 导入 useAlerts hook**

修改 import：
```typescript
import {
  useProducts, useCreateProduct, useUpdateProduct, useDeleteProduct,
  useBatchCreate, useBatchDelete, useBatchUpdate, useCrawlNow, useAlerts,
} from '@/hooks/api'
```

- [ ] **Step 2: 添加告警数据获取**

在组件中添加：
```typescript
const { data: alertsData } = useAlerts(undefined as unknown as undefined)
const alertMap = useMemo(() => {
  const map = new Map<number, { threshold_percent: number; active: boolean }>()
  alertsData?.forEach((alert) => {
    map.set(alert.product_id, {
      threshold_percent: alert.threshold_percent || 0,
      active: alert.active,
    })
  })
  return map
}, [alertsData])
```

- [ ] **Step 3: 在 columns 中添加「告警」列**

在 columns 定义中添加（放在「状态」列后面）：
```typescript
{
  title: '告警',
  key: 'alert',
  width: 80,
  render: (_: any, record: Product) => {
    const alert = alertMap.get(record.id)
    if (!alert) return <Tag>未设置</Tag>
    return alert.active ? (
      <Tag color="orange">{String(alert.threshold_percent)}%</Tag>
    ) : (
      <Tag color="default">{String(alert.threshold_percent)}% (停用)</Tag>
    )
  },
},
```

- [ ] **Step 4: 调整操作列宽度**

将操作列宽度从 `320` 改为 `380` 以容纳新增列

- [ ] **Step 5: 验证 TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ProductsPage.tsx
git commit -m "feat(frontend): 在商品列表显示告警状态列"
```

---

## Task 5: 在商品编辑弹窗集成告警区块

**Files:**
- Modify: `frontend/src/components/ProductFormModal.tsx`

- [ ] **Step 1: 添加告警相关 imports**

```typescript
import { useAlerts, useCreateAlert, useUpdateAlert, useDeleteAlert } from '@/hooks/api'
import { Switch, InputNumber, Button, Divider, Space, Popconfirm } from 'antd'
import { AlertOutlined, DeleteOutlined } from '@ant-design/icons'
import { alertsApi } from '@/api/alerts'
```

- [ ] **Step 2: 添加告警状态和 mutations**

在组件中添加：
```typescript
const { data: alertData, refetch: refetchAlert } = useAlerts(record?.id)
const createAlertMutation = useCreateAlert()
const updateAlertMutation = useUpdateAlert()
const deleteAlertMutation = useDeleteAlert()

const [alertEnabled, setAlertEnabled] = useState(false)
const [alertThreshold, setAlertThreshold] = useState(5)
const [currentAlertId, setCurrentAlertId] = useState<number | null>(null)
```

- [ ] **Step 3: 当 record 或 alertData 变化时更新告警状态**

```typescript
useEffect(() => {
  if (alertData && alertData.length > 0) {
    const alert = alertData[0]
    setCurrentAlertId(alert.id)
    setAlertEnabled(alert.active)
    setAlertThreshold(Number(alert.threshold_percent) || 5)
  } else {
    setCurrentAlertId(null)
    setAlertEnabled(false)
    setAlertThreshold(5)
  }
}, [alertData])
```

- [ ] **Step 4: 添加告警区块 UI**

在 Modal 的 Form 内容之后添加（关闭 `</Form>` 标签后）：

```tsx
<Divider orientation="left" plain>
  <Space>
    <AlertOutlined />
    价格告警设置
  </Space>
</Divider>

<Space direction="vertical" style={{ width: '100%' }}>
  <Space>
    <span>启用告警：</span>
    <Switch
      checked={alertEnabled}
      onChange={async (checked) => {
        setAlertEnabled(checked)
        if (currentAlertId) {
          await updateAlertMutation.mutateAsync({
            id: currentAlertId,
            data: { active: checked },
          })
          refetchAlert()
        } else if (checked) {
          const res = await createAlertMutation.mutateAsync({
            product_id: record!.id,
            threshold_percent: alertThreshold,
            active: true,
          })
          setCurrentAlertId(res.id)
          refetchAlert()
        }
      }}
    />
  </Space>

  <Space>
    <span>降价阈值：</span>
    <InputNumber
      min={1}
      max={100}
      value={alertThreshold}
      onChange={(val) => setAlertThreshold(val || 5)}
      disabled={!currentAlertId}
      addonAfter="%"
      style={{ width: 120 }}
    />
    <Button
      size="small"
      onClick={async () => {
        if (currentAlertId) {
          await updateAlertMutation.mutateAsync({
            id: currentAlertId,
            data: { threshold_percent: alertThreshold },
          })
          refetchAlert()
        }
      }}
    >
      保存阈值
    </Button>
  </Space>

  {currentAlertId && (
    <Popconfirm
      title="确定删除此商品的告警？"
      onConfirm={async () => {
        await deleteAlertMutation.mutateAsync(currentAlertId)
        setCurrentAlertId(null)
        setAlertEnabled(false)
        refetchAlert()
      }}
    >
      <Button size="small" danger icon={<DeleteOutlined />}>
        删除告警
      </Button>
    </Popconfirm>
  )}
</Space>
```

- [ ] **Step 5: 验证 TypeScript**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ProductFormModal.tsx
git commit -m "feat(frontend): 在商品编辑弹窗集成告警管理"
```

---

## Task 6: 整体验证

- [ ] **Step 1: 启动前端验证**

Run: `cd frontend && npm run dev`

- [ ] **Step 2: 测试告警列显示**

打开商品管理页，验证「告警」列正确显示阈值或「未设置」

- [ ] **Step 3: 测试创建告警**

点击商品「编辑」→ 在弹窗中启用告警 → 验证告警创建成功

- [ ] **Step 4: 测试编辑告警阈值**

修改阈值 → 点击保存 → 验证更新成功

- [ ] **Step 5: 测试删除告警**

点击删除 → 验证告警删除成功，列表中显示「未设置」

---

## 验收标准

1. 商品列表显示「告警」列，显示阈值或「未设置」
2. 编辑商品弹窗底部有「价格告警设置」区块
3. 可以启用/停用告警
4. 可以修改告警阈值
5. 可以删除告警
6. TypeScript 编译通过
