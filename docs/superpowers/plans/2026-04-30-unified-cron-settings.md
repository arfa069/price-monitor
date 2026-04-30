# Unified Cron Settings Card — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify product crawl cron and job crawl cron into a single "Cron 定时配置" card on ScheduleConfigPage, removing duplicate components from ProductsPage and JobsPage.

**Architecture:** Refactor ScheduleConfigPage from 2 cards into 3 cards. The new middle card fetches both `GET /config` and `GET /scheduler/status`, displays product + job cron side by side with independent save buttons, and shows live next-run times. The two standalone components (`ProductCrawlSettings`, `CronSettings`) are deleted.

**Tech Stack:** React + TypeScript + Ant Design (Card, Input, Button, Space, Divider, message, Spin) + TanStack React Query + Axios

---

## File Structure

| File | Responsibility |
|------|---------------|
| `frontend/src/types/index.ts` | Add `SchedulerStatusResponse` type + `job_crawl_cron` to `UserConfig` |
| `frontend/src/api/config.ts` | Add `getSchedulerStatus()` method |
| `frontend/src/pages/ScheduleConfigPage.tsx` | Full rewrite — 3 cards, unified cron card, no drafts |
| `frontend/src/components/ProductCrawlSettings.tsx` | DELETE — superseded |
| `frontend/src/components/CronSettings.tsx` | DELETE — superseded |
| `frontend/src/pages/ProductsPage.tsx` | Remove `ProductCrawlSettings` import + usage |
| `frontend/src/pages/JobsPage.tsx` | Remove `CronSettings` import + usage |

---

### Task 1: Add types and API client method

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/config.ts`

- [ ] **Step 1: Add `SchedulerStatusResponse` type and `job_crawl_cron` to `UserConfig`**

In `frontend/src/types/index.ts`, add after `UserConfig`:

```typescript
export interface SchedulerJobStatus {
  registered: boolean
  cron_expression: string | null
  next_run_at: string | null
}

export interface SchedulerStatusResponse {
  scheduler: string
  timezone: string
  jobs: {
    product_crawl: SchedulerJobStatus
    job_crawl: SchedulerJobStatus
  }
}
```

Also add `job_crawl_cron` field to `UserConfig` interface (between `crawl_timezone` and `created_at`):

```typescript
  job_crawl_cron: string | null
```

- [ ] **Step 2: Add `getSchedulerStatus` to configApi**

In `frontend/src/api/config.ts`, add after `updateJobCrawlCron`:

```typescript
  getSchedulerStatus: () =>
    api.get<SchedulerStatusResponse>('/scheduler/status'),
```

Import `SchedulerStatusResponse` at the top:

```typescript
import type { SchedulerStatusResponse, UserConfig } from '@/types'
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/config.ts
git commit -m "feat(frontend): add SchedulerStatus type and getSchedulerStatus API"
```

---

### Task 2: Delete cron components and clean up references

**Files:**
- Delete: `frontend/src/components/ProductCrawlSettings.tsx`
- Delete: `frontend/src/components/CronSettings.tsx`
- Modify: `frontend/src/pages/ProductsPage.tsx:58,437`
- Modify: `frontend/src/pages/JobsPage.tsx:12,92`

- [ ] **Step 1: Delete the two component files**

```bash
git rm frontend/src/components/ProductCrawlSettings.tsx frontend/src/components/CronSettings.tsx
```

- [ ] **Step 2: Remove ProductCrawlSettings from ProductsPage**

In `frontend/src/pages/ProductsPage.tsx`, delete the import:
```typescript
import ProductCrawlSettings from '@/components/ProductCrawlSettings'
```

Delete the usage and surrounding blank line:
```tsx
      <ProductCrawlSettings />

```

- [ ] **Step 3: Remove CronSettings from JobsPage**

In `frontend/src/pages/JobsPage.tsx`, delete the import:
```typescript
import CronSettings from '@/components/CronSettings'
```

Delete the usage and surrounding blank line:
```tsx
      <CronSettings />

```

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors (all changes done atomically, no intermediate breakage)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ProductCrawlSettings.tsx frontend/src/components/CronSettings.tsx frontend/src/pages/ProductsPage.tsx frontend/src/pages/JobsPage.tsx
git commit -m "chore(frontend): remove ProductCrawlSettings and CronSettings superseded by unified card"
```

---

### Task 3: Refactor ScheduleConfigPage — Part 1 (data fetching + cron card)

**Files:**
- Modify: `frontend/src/pages/ScheduleConfigPage.tsx` (full rewrite)

- [ ] **Step 1: Replace imports and remove draft constants**

Replace current imports (lines 1-15) with:

```typescript
import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Divider,
  Form,
  Input,
  InputNumber,
  Radio,
  Skeleton,
  Space,
  Spin,
  message,
} from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import { useConfig, useUpdateConfig } from '@/hooks/api'
import { configApi } from '@/api/config'
import type { SchedulerJobStatus } from '@/types'

type ScheduleMode = 'hours' | 'cron'

const CRON_SEGMENT_RE = /^\*|[0-9]+(?:-[0-9]+)?(?:\/[0-9]+)?$/

const isValidCronFormat = (value: string): boolean => {
  const parts = value.trim().split(/\s+/)
  if (parts.length !== 5) return false
  return parts.every((part) => CRON_SEGMENT_RE.test(part))
}

type ScheduleFormValues = {
  schedule_mode: ScheduleMode
  crawl_frequency_hours?: number
  data_retention_days?: number
}
```

Note: `crawl_cron` and `crawl_timezone` are removed from `ScheduleFormValues` — they're managed in the new cron card. `UndoOutlined`, `DeleteOutlined`, localStorage draft keys, and `draftDismissed` state are all gone.

- [ ] **Step 2: Replace the component body — state and data fetching**

Replace the entire component function body. The new structure:

```typescript
export default function ScheduleConfigPage() {
  const { data: config, isLoading, isError, refetch } = useConfig()
  const updateMutation = useUpdateConfig()
  const [form] = Form.useForm<ScheduleFormValues>()

  // Cron card state (uncontrolled until save)
  const [productCron, setProductCron] = useState('')
  const [productTz, setProductTz] = useState('Asia/Shanghai')
  const [jobCron, setJobCron] = useState('')
  const [productCronSaving, setProductCronSaving] = useState(false)
  const [jobCronSaving, setJobCronSaving] = useState(false)

  // Scheduler status
  const [schedulerJobs, setSchedulerJobs] = useState<Record<string, SchedulerJobStatus>>({})
  const [schedulerLoading, setSchedulerLoading] = useState(true)
  const [schedulerError, setSchedulerError] = useState(false)

  const fetchSchedulerStatus = async () => {
    setSchedulerLoading(true)
    setSchedulerError(false)
    try {
      const res = await configApi.getSchedulerStatus()
      if (res.status === 200) {
        setSchedulerJobs(res.data.jobs)
      }
    } catch {
      setSchedulerError(true)
      setSchedulerJobs({})
    } finally {
      setSchedulerLoading(false)
    }
  }

  // Populate form and cron inputs from config
  useEffect(() => {
    if (!config) return
    form.setFieldsValue({
      schedule_mode: config.crawl_cron ? 'cron' : 'hours',
      crawl_frequency_hours: config.crawl_frequency_hours || 1,
      data_retention_days: config.data_retention_days || 365,
    })
    setProductCron(config.crawl_cron || '')
    setProductTz(config.crawl_timezone || 'Asia/Shanghai')
    setJobCron(config.job_crawl_cron || '')
  }, [config, form])

  // Fetch scheduler status on mount and after config save
  useEffect(() => {
    fetchSchedulerStatus()
  }, [])

  const scheduleMode =
    Form.useWatch('schedule_mode', form) ?? (config?.crawl_cron ? 'cron' : 'hours')
  const cronInput = productCron
  const cronValid = useMemo(
    () => (cronInput.trim() ? isValidCronFormat(cronInput) : null),
    [cronInput],
  )
```

The key design decisions here:
- `productCron`, `productTz`, `jobCron` are plain `useState` — not backed by Form — because they save independently via different API calls
- `fetchSchedulerStatus` is a standalone function so it can be called on mount AND after any save
- No localStorage draft logic at all

- [ ] **Step 3: Replace save handlers and cron change handler**

```typescript
  const handleSaveHours = async (values: ScheduleFormValues) => {
    try {
      await updateMutation.mutateAsync({
        crawl_frequency_hours: values.crawl_frequency_hours,
        data_retention_days: values.data_retention_days,
      })
      message.success('配置已保存')
      refetch()
    } catch {
      message.error('保存失败')
    }
  }

  const handleSaveProductCron = async () => {
    if (cronValid !== true) {
      message.error('Cron 表达式不合法')
      return
    }
    setProductCronSaving(true)
    try {
      await configApi.update({ crawl_cron: productCron.trim(), crawl_timezone: productTz })
      message.success('商品爬取 Cron 已保存')
      refetch()
      fetchSchedulerStatus()
    } catch {
      message.error('保存失败')
    } finally {
      setProductCronSaving(false)
    }
  }

  const handleSaveJobCron = async () => {
    const value = jobCron.trim() || null
    if (value && !isValidCronFormat(value)) {
      message.error('Cron 表达式不合法')
      return
    }
    setJobCronSaving(true)
    try {
      await configApi.updateJobCrawlCron(value)
      message.success('职位爬取 Cron 已保存')
      refetch()
      fetchSchedulerStatus()
    } catch {
      message.error('保存失败')
    } finally {
      setJobCronSaving(false)
    }
  }
```

Each save:
1. Re-fetches `/config` (via `refetch()`) to get the confirmed backend values
2. Re-fetches `/scheduler/status` (via `fetchSchedulerStatus()`) to update next-run times
3. Shows independent loading state per button

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ScheduleConfigPage.tsx
git commit -m "refactor(frontend): restructure ScheduleConfigPage data layer for unified cron card"
```

---

### Task 4: Refactor ScheduleConfigPage — Part 2 (JSX: three cards)

**Files:**
- Modify: `frontend/src/pages/ScheduleConfigPage.tsx` (replace JSX return block)

- [ ] **Step 1: Replace the entire JSX return block**

Replace everything from `return (` to the closing `)` of the component with:

```tsx
  const formatNextRun = (job: SchedulerJobStatus | undefined): string => {
    if (schedulerError) return '调度器未启动'
    if (!job?.registered) return '未注册'
    if (!job.next_run_at) return '待定'
    return new Date(job.next_run_at).toLocaleString('zh-CN')
  }

  return (
    <div>
      <h1
        style={{
          fontSize: 24,
          color: '#1f2937',
          marginBottom: 24,
          fontWeight: 500,
        }}
      >
        定时配置
      </h1>

      {isError && !isLoading && (
        <Alert
          type="error"
          message="加载失败"
          description="无法获取配置，请检查网络或稍后重试。"
          action={
            <Button size="small" onClick={() => refetch()}>
              重试
            </Button>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      <Form form={form} layout="vertical" onFinish={handleSaveHours}>
        {isLoading && !config ? (
          <Card title="抓取频率配置">
            <Skeleton active paragraph={{ rows: 4 }} />
          </Card>
        ) : (
          <Card title="抓取频率配置">
            <Form.Item name="schedule_mode" label="调度模式" style={{ marginBottom: 16 }}>
              <Radio.Group>
                <Radio.Button value="hours">间隔模式</Radio.Button>
                <Radio.Button value="cron">Cron 模式</Radio.Button>
              </Radio.Group>
            </Form.Item>

            {scheduleMode === 'hours' && (
              <>
                <Form.Item
                  name="crawl_frequency_hours"
                  label="每隔几小时执行一次"
                  rules={[{ required: true, message: '请输入小时数' }]}
                >
                  <Space.Compact style={{ width: '100%' }}>
                    <InputNumber min={1} max={168} style={{ width: '100%' }} />
                    <Input value="小时" disabled style={{ width: 60 }} />
                  </Space.Compact>
                </Form.Item>
                <Form.Item>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    htmlType="submit"
                    loading={updateMutation.isPending}
                  >
                    保存配置
                  </Button>
                </Form.Item>
              </>
            )}

            {scheduleMode === 'cron' && (
              <Alert
                message="Cron 模式已启用"
                description="Cron 表达式请在下方「Cron 定时配置」卡片中编辑。"
                type="info"
                showIcon
              />
            )}
          </Card>
        )}
      </Form>

      <Card title="Cron 定时配置" style={{ marginTop: 24 }}>
        {isLoading && !config ? (
          <Skeleton active paragraph={{ rows: 4 }} />
        ) : (
          <>
            {/* ── Product Crawl Cron ── */}
            <div>
              <h4 style={{ marginBottom: 12, color: '#1f2937' }}>商品爬取</h4>
              <Space wrap>
                <Input
                  value={productCron}
                  onChange={(e) => setProductCron(e.target.value)}
                  placeholder="0 9 * * *"
                  style={{ width: 200 }}
                  autoComplete="off"
                  name="product-cron"
                />
                <Input
                  value={productTz}
                  onChange={(e) => setProductTz(e.target.value)}
                  placeholder="Asia/Shanghai"
                  style={{ width: 160 }}
                  autoComplete="off"
                  name="product-timezone"
                />
                <Button
                  type="primary"
                  onClick={handleSaveProductCron}
                  disabled={cronValid !== true}
                  loading={productCronSaving}
                >
                  保存
                </Button>
              </Space>
              {cronValid === false && (
                <Alert
                  message="Cron 表达式不合法，请使用 5 段格式（分 时 日 月 周）"
                  type="error"
                  showIcon
                  style={{ marginTop: 8 }}
                />
              )}
              <div style={{ marginTop: 8, color: '#888', fontSize: 12 }}>
                下次执行:{' '}
                {schedulerLoading ? (
                  <Spin size="small" />
                ) : (
                  formatNextRun(schedulerJobs.product_crawl)
                )}
              </div>
            </div>

            <Divider style={{ margin: '16px 0' }} />

            {/* ── Job Crawl Cron ── */}
            <div>
              <h4 style={{ marginBottom: 12, color: '#1f2937' }}>职位爬取</h4>
              <Space wrap>
                <Input
                  value={jobCron}
                  onChange={(e) => setJobCron(e.target.value)}
                  placeholder="0 9 * * *"
                  style={{ width: 200 }}
                  autoComplete="off"
                  name="job-cron"
                />
                <Button
                  type="primary"
                  onClick={handleSaveJobCron}
                  disabled={jobCron.trim() !== '' && !isValidCronFormat(jobCron)}
                  loading={jobCronSaving}
                >
                  保存
                </Button>
              </Space>
              {jobCron.trim() !== '' && !isValidCronFormat(jobCron) && (
                <Alert
                  message="Cron 表达式不合法，请使用 5 段格式（分 时 日 月 周）"
                  type="error"
                  showIcon
                  style={{ marginTop: 8 }}
                />
              )}
              <div style={{ marginTop: 8, color: '#888', fontSize: 12 }}>
                下次执行:{' '}
                {schedulerLoading ? (
                  <Spin size="small" />
                ) : (
                  formatNextRun(schedulerJobs.job_crawl)
                )}
              </div>
            </div>
          </>
        )}
      </Card>

      {isLoading && !config ? (
        <Card title="数据保留与其他配置" style={{ marginTop: 24 }}>
          <Skeleton active paragraph={{ rows: 2 }} />
        </Card>
      ) : (
        <Card title="数据保留与其他配置" style={{ marginTop: 24 }}>
          <Form form={form} layout="vertical" onFinish={handleSaveHours}>
            <Form.Item
              name="data_retention_days"
              label="数据保留天数"
              rules={[{ required: true, message: '请输入天数' }]}
            >
              <Space.Compact style={{ width: '100%' }}>
                <InputNumber min={1} max={3650} style={{ width: '100%' }} />
                <Input value="天" disabled style={{ width: 60 }} />
              </Space.Compact>
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                htmlType="submit"
                loading={updateMutation.isPending}
              >
                保存配置
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}
    </div>
  )
}
```

Note: The old `draftDismissed` state, `pendingDraft` memo, `handleRestoreDraft`, `handleDiscardDraft`, `handleCronChange`, `handleSaveCron`, `handleSaveDraft` are all removed. The draft alert (`pendingDraft && ...`) is removed.

- [ ] **Step 2: Type-check and lint**

Run:
```
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ScheduleConfigPage.tsx
git commit -m "feat(frontend): add unified Cron timer card to ScheduleConfigPage"
```

---

### Task 5: Automated verification

- [ ] **Step 1: Full type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 2: Lint**

Run: `cd frontend && npm run lint`
Expected: no errors

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 4: Verify no stale references**

```bash
git grep "ProductCrawlSettings" frontend/
git grep "CronSettings" frontend/
```

Expected: no matches

- [ ] **Step 5: Commit (if any lint/build fixes)**

```bash
git commit -m "chore(frontend): final cleanup for unified cron card"
```

---

### Task 6: Manual QA verification

The frontend has no test framework (no vitest/jest in `package.json`).
Before claiming completion, verify these paths manually in the browser.

**Prerequisite:** Start backend + frontend dev servers.

- [ ] **Step 1: Page loads with config (happy path)**

Navigate to the 定时配置 page.
Expected: Three cards visible. Cron card shows product cron input, timezone input, job cron input, and next-run times (not "调度器未启动").

- [ ] **Step 2: Product cron — save valid expression**

Enter `0 10 * * *` in product cron, change timezone to `Asia/Tokyo`, click 保存.
Expected: "商品爬取 Cron 已保存" toast. After save, inputs retain new values. Next-run time updates (may show "未注册" if scheduler hasn't picked up new cron yet — that's OK).

- [ ] **Step 3: Product cron — reject invalid expression**

Enter `invalid` in product cron, blur the input.
Expected: Save button is disabled. Red error alert "Cron 表达式不合法" appears below inputs.

- [ ] **Step 4: Job cron — save valid expression**

Enter `30 8 * * 1-5` in job cron, click 保存.
Expected: "职位爬取 Cron 已保存" toast.

- [ ] **Step 5: Job cron — save empty (use default)**

Clear the job cron input, click 保存.
Expected: "职位爬取 Cron 已保存" toast. After refetch, input shows empty (backend returns null, frontend shows placeholder "0 9 * * *").

- [ ] **Step 6: Interval mode still works**

Switch to 间隔模式, change hours to `3`, click 保存配置.
Expected: "配置已保存" toast. Cron card remains visible below.

- [ ] **Step 7: Error state — scheduler unavailable**

Stop the backend server. Reload the page.
Expected (for cron card): Next-run displays show "调度器未启动" for both product and job. Error alert at top shows "加载失败" with 重试 button.

- [ ] **Step 8: Stale references cleaned**

Browse to 商品管理 page. Expected: Page loads normally, no blank space where ProductCrawlSettings was.
Browse to 职位管理 page. Expected: Page loads normally, no blank space where CronSettings was.

- [ ] **Step 9: Commit any QA-driven fixes**

```bash
git add -A && git commit -m "chore(frontend): manual QA verification fixes for unified cron card"
```

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAN (PLAN) | 3 issues: arch 0, code quality 2 (minor), perf 0 |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **CODEX:** not run
- **OUTSIDE VOICE:** Claude subagent — 9 findings, 2 rejected (#1 design decision upheld, #9 Axios correctly handles 503), 2 fixes applied (#5 tasks merged, #6 timezone bug fixed), 5 noted (#2 acknowledged UX tradeoff per user decision A, #3 cache strategy inconsistency deferred, #4 backend PATCH trap logged, #7 refresh race minor, #8 layout gap minor)
- **CROSS-MODEL TENSION:** None — all actionable findings resolved
- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED — ready to implement
- **Note:** Prior web-design-guidelines review caught 2 consistency issues (emoji + color), fixed in plan v2 before eng review
- **TODOS:** 1 created — frontend test framework setup deferred to `TODOS.md`
