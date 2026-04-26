# Boss 直聘职位爬虫前端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Boss 直聘职位爬虫系统的前端管理界面，包括搜索配置管理和职位列表查看。

**Architecture:** 沿用现有前端架构（React + Ant Design + React Query），创建独立页面组件，配置路由和侧边栏入口。

**Tech Stack:** React 18 + TypeScript + Ant Design 5.x + React Router 6 + React Query

---

## 文件映射

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 创建 | `frontend/src/api/jobs.ts` | 职位 API 封装 |
| 修改 | `frontend/src/types/index.ts` | 添加 Job/JobSearchConfig 类型 |
| 修改 | `frontend/src/hooks/api.ts` | 添加职位相关 hooks |
| 创建 | `frontend/src/components/JobConfigForm.tsx` | 配置表单组件 |
| 创建 | `frontend/src/components/JobConfigList.tsx` | 配置卡片列表组件 |
| 创建 | `frontend/src/components/JobDrawer.tsx` | 职位详情抽屉组件 |
| 创建 | `frontend/src/components/JobList.tsx` | 职位表格组件 |
| 创建 | `frontend/src/pages/JobsPage.tsx` | 主页面 |
| 修改 | `frontend/src/App.tsx` | 添加路由和菜单 |
| 修改 | `frontend/src/components/AppLayout.tsx` | 添加职位管理菜单 |

---

## Task 1: 添加类型定义

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 添加 JobSearchConfig 类型**

在 `types/index.ts` 末尾添加：

```typescript
export interface JobSearchConfig {
  id: number
  user_id: number
  name: string
  keyword: string | null
  city_code: string | null
  salary_min: number | null
  salary_max: number | null
  experience: string | null
  education: string | null
  url: string
  active: boolean
  notify_on_new: boolean
  created_at: string
  updated_at: string
}

export interface JobSearchConfigCreate {
  name: string
  keyword?: string
  city_code?: string
  salary_min?: number
  salary_max?: number
  experience?: string
  education?: string
  url: string
  active?: boolean
  notify_on_new?: boolean
}

export interface JobSearchConfigUpdate {
  name?: string
  keyword?: string
  city_code?: string
  salary_min?: number
  salary_max?: number
  experience?: string
  education?: string
  url?: string
  active?: boolean
  notify_on_new?: boolean
}

export interface Job {
  id: number
  job_id: string
  search_config_id: number
  title: string | null
  company: string | null
  company_id: string | null
  salary: string | null
  salary_min: number | null
  salary_max: number | null
  location: string | null
  experience: string | null
  education: string | null
  description: string | null
  url: string | null
  first_seen_at: string
  last_updated_at: string
  is_active: boolean
}

export interface JobCrawlResult {
  new_count: number
  updated_count: number
  deactivated_count: number
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(frontend): add job crawler types"
```

---

## Task 2: 创建 API 模块

**Files:**
- Create: `frontend/src/api/jobs.ts`

- [ ] **Step 1: 创建 jobs.ts**

```typescript
import api from './client'
import type {
  JobSearchConfig,
  JobSearchConfigCreate,
  JobSearchConfigUpdate,
  Job,
  JobCrawlResult,
} from '@/types'

export const jobsApi = {
  // JobSearchConfig APIs
  getConfigs: (active?: boolean) =>
    api.get<JobSearchConfig[]>('/jobs/configs', {
      params: active !== undefined ? { active } : undefined,
    }),

  getConfig: (id: number) =>
    api.get<JobSearchConfig>(`/jobs/configs/${id}`),

  createConfig: (data: JobSearchConfigCreate) =>
    api.post<JobSearchConfig>('/jobs/configs', data),

  updateConfig: (id: number, data: JobSearchConfigUpdate) =>
    api.patch<JobSearchConfig>(`/jobs/configs/${id}`, data),

  deleteConfig: (id: number) =>
    api.delete(`/jobs/configs/${id}`),

  // Job APIs
  getJobs: (params?: {
    search_config_id?: number
    keyword?: string
    company?: string
    salary_min?: number
    salary_max?: number
    location?: string
    is_active?: boolean
    sort_by?: string
    sort_order?: string
    page?: number
    page_size?: number
  }) => api.get<Job[]>('/jobs', { params }),

  getJob: (jobId: string) =>
    api.get<Job>(`/jobs/${jobId}`),

  // Crawl APIs
  crawlAll: () =>
    api.post<{ status: string; total: number; success: number; errors: number }>('/jobs/crawl-now'),

  crawlSingle: (configId: number) =>
    api.post<JobCrawlResult>(`/jobs/crawl-now/${configId}`),
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/jobs.ts
git commit -m "feat(frontend): add jobs API module"
```

---

## Task 3: 添加 Hooks

**Files:**
- Modify: `frontend/src/hooks/api.ts`

- [ ] **Step 1: 添加 JobSearchConfig hooks**

在 `hooks/api.ts` 末尾添加：

```typescript
// JobSearchConfig hooks
export const useJobConfigs = (active?: boolean) => {
  return useQuery({
    queryKey: ['job-configs', active],
    queryFn: () => jobsApi.getConfigs(active).then((res) => res.data),
  })
}

export const useJobConfig = (id: number) => {
  return useQuery({
    queryKey: ['job-config', id],
    queryFn: () => jobsApi.getConfig(id).then((res) => res.data),
    enabled: !!id,
  })
}

export const useCreateJobConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.createConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-configs'] }),
  })
}

export const useUpdateJobConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: JobSearchConfigUpdate }) =>
      jobsApi.updateConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-configs'] }),
  })
}

export const useDeleteJobConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.deleteConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-configs'] }),
  })
}

// Job hooks
export const useJobs = (params?: {
  search_config_id?: number
  keyword?: string
  company?: string
  salary_min?: number
  salary_max?: number
  location?: string
  is_active?: boolean
  sort_by?: string
  sort_order?: string
  page?: number
  page_size?: number
}) => {
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: () => jobsApi.getJobs(params).then((res) => res.data),
    staleTime: 30_000,
  })
}

export const useJob = (jobId: string) => {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.getJob(jobId).then((res) => res.data),
    enabled: !!jobId,
  })
}

// Job crawl hooks
export const useCrawlAllJobs = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.crawlAll,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export const useCrawlSingleJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.crawlSingle,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}
```

- [ ] **Step 2: 添加 import**

在 `hooks/api.ts` 顶部添加：

```typescript
import { jobsApi } from '@/api/jobs'
import type { JobSearchConfigUpdate } from '@/types'
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/hooks/api.ts
git commit -m "feat(frontend): add job crawler hooks"
```

---

## Task 4: 创建配置表单组件

**Files:**
- Create: `frontend/src/components/JobConfigForm.tsx`

- [ ] **Step 1: 创建 JobConfigForm.tsx**

```typescript
import { useEffect } from 'react'
import {
  Modal, Form, Input, InputNumber, Switch, Button, Space, message,
} from 'antd'
import type { JobSearchConfig, JobSearchConfigCreate, JobSearchConfigUpdate } from '@/types'

interface JobConfigFormProps {
  open: boolean
  record?: JobSearchConfig | null
  onCancel: () => void
  onSubmit: (values: JobSearchConfigCreate) => Promise<void>
  confirmLoading?: boolean
}

export default function JobConfigForm({
  open,
  record,
  onCancel,
  onSubmit,
  confirmLoading,
}: JobConfigFormProps) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (open) {
      if (record) {
        form.setFieldsValue(record)
      } else {
        form.resetFields()
        form.setFieldsValue({
          active: true,
          notify_on_new: true,
        })
      }
    }
  }, [open, record, form])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      await onSubmit(values as JobSearchConfigCreate)
      form.resetFields()
    } catch (err) {
      // 表单验证失败
    }
  }

  return (
    <Modal
      title={record ? '编辑搜索配置' : '新增搜索配置'}
      open={open}
      onCancel={onCancel}
      onOk={handleOk}
      confirmLoading={confirmLoading}
      width={500}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        style={{ marginTop: 16 }}
      >
        <Form.Item
          name="name"
          label="配置名称"
          rules={[{ required: true, message: '请输入配置名称' }]}
        >
          <Input placeholder="如：北京 Python 开发" />
        </Form.Item>

        <Form.Item
          name="url"
          label="Boss 直聘搜索 URL"
          rules={[{ required: true, message: '请输入搜索页 URL' }]}
          extra="在 Boss 直聘网站筛选后复制完整 URL"
        >
          <Input placeholder="https://www.zhipin.com/web/geek/job?query=python&city=101010100" />
        </Form.Item>

        <Form.Item name="keyword" label="关键词（可选）">
          <Input placeholder="如：Python, 后端" />
        </Form.Item>

        <Form.Item name="city_code" label="城市代码（可选）">
          <Input placeholder="如：101010100（北京）" />
        </Form.Item>

        <Space style={{ width: '100%' }} size={16}>
          <Form.Item name="salary_min" label="最低薪资（K）" style={{ width: 120 }}>
            <InputNumber min={0} placeholder="如：20" />
          </Form.Item>
          <Form.Item name="salary_max" label="最高薪资（K）" style={{ width: 120 }}>
            <InputNumber min={0} placeholder="如：50" />
          </Form.Item>
        </Space>

        <Form.Item name="experience" label="经验要求（可选）">
          <Input placeholder="如：3-5年" />
        </Form.Item>

        <Form.Item name="education" label="学历要求（可选）">
          <Input placeholder="如：本科" />
        </Form.Item>

        <Form.Item name="active" label="启用" valuePropName="checked" initialValue={true}>
          <Switch />
        </Form.Item>

        <Form.Item name="notify_on_new" label="新职位通知" valuePropName="checked" initialValue={true}>
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/JobConfigForm.tsx
git commit -m "feat(frontend): add JobConfigForm component"
```

---

## Task 5: 创建配置列表组件

**Files:**
- Create: `frontend/src/components/JobConfigList.tsx`

- [ ] **Step 1: 创建 JobConfigList.tsx**

```typescript
import { useState } from 'react'
import { Card, Button, Space, Tag, Popconfirm, message, Spin } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, RocketOutlined } from '@ant-design/icons'
import type { JobSearchConfig, JobSearchConfigCreate } from '@/types'
import JobConfigForm from './JobConfigForm'

interface JobConfigListProps {
  configs: JobSearchConfig[] | undefined
  isLoading: boolean
  onCreate: (data: JobSearchConfigCreate) => Promise<void>
  onUpdate: (id: number, data: Partial<JobSearchConfigCreate>) => Promise<void>
  onDelete: (id: number) => Promise<void>
  onCrawl: (id: number) => Promise<void>
  createLoading?: boolean
  updateLoading?: boolean
  crawlLoading?: number | null
}

export default function JobConfigList({
  configs,
  isLoading,
  onCreate,
  onUpdate,
  onDelete,
  onCrawl,
  createLoading,
  updateLoading,
  crawlLoading,
}: JobConfigListProps) {
  const [formOpen, setFormOpen] = useState(false)
  const [editRecord, setEditRecord] = useState<JobSearchConfig | null>(null)

  const handleFormSubmit = async (values: JobSearchConfigCreate) => {
    if (editRecord) {
      await onUpdate(editRecord.id, values)
      message.success('更新成功')
    } else {
      await onCreate(values)
      message.success('创建成功')
    }
    setFormOpen(false)
    setEditRecord(null)
  }

  const handleEdit = (record: JobSearchConfig) => {
    setEditRecord(record)
    setFormOpen(true)
  }

  const handleDelete = async (id: number) => {
    await onDelete(id)
    message.success('删除成功')
  }

  const handleCrawl = async (id: number) => {
    await onCrawl(id)
    message.success('爬取完成')
  }

  if (isLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>搜索配置</h3>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditRecord(null); setFormOpen(true) }}>
          新增配置
        </Button>
      </div>

      {!configs || configs.length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b' }}>
            暂无搜索配置，点击上方按钮添加
          </div>
        </Card>
      ) : (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {configs.map((config) => (
            <Card
              key={config.id}
              style={{
                width: 260,
                background: config.active
                  ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                  : '#94a3b8',
                color: '#fff',
              }}
              bodyStyle={{ padding: 16 }}
            >
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>
                {config.name}
              </div>

              {config.keyword && (
                <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 4 }}>
                  关键词：{config.keyword}
                </div>
              )}

              {config.salary_min || config.salary_max ? (
                <div style={{ fontSize: 12, opacity: 0.9, marginBottom: 4 }}>
                  薪资：{config.salary_min || '?'}-{config.salary_max || '?'}K
                </div>
              ) : null}

              <div
                style={{
                  fontSize: 11,
                  opacity: 0.7,
                  marginBottom: 12,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={config.url}
              >
                {config.url}
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <Button
                  size="small"
                  style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', border: 'none' }}
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(config)}
                >
                  编辑
                </Button>
                <Button
                  size="small"
                  style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', border: 'none' }}
                  icon={<RocketOutlined />}
                  loading={crawlLoading === config.id}
                  onClick={() => handleCrawl(config.id)}
                >
                  爬取
                </Button>
                <Popconfirm
                  title="确定删除此配置？"
                  onConfirm={() => handleDelete(config.id)}
                >
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                  >
                    删除
                  </Button>
                </Popconfirm>
              </div>
            </Card>
          ))}
        </div>
      )}

      <JobConfigForm
        open={formOpen}
        record={editRecord}
        onCancel={() => { setFormOpen(false); setEditRecord(null) }}
        onSubmit={handleFormSubmit}
        confirmLoading={createLoading || updateLoading}
      />
    </div>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/JobConfigList.tsx
git commit -m "feat(frontend): add JobConfigList component"
```

---

## Task 6: 创建职位详情抽屉组件

**Files:**
- Create: `frontend/src/components/JobDrawer.tsx`

- [ ] **Step 1: 创建 JobDrawer.tsx**

```typescript
import { Drawer, Descriptions, Tag, Button, Spin } from 'antd'
import { ExternalLinkOutlined } from '@ant-design/icons'
import type { Job } from '@/types'

interface JobDrawerProps {
  open: boolean
  job: Job | null
  loading?: boolean
  onClose: () => void
}

export default function JobDrawer({ open, job, loading, onClose }: JobDrawerProps) {
  return (
    <Drawer
      title="职位详情"
      placement="right"
      width={500}
      open={open}
      onClose={onClose}
    >
      {loading ? (
        <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />
      ) : job ? (
        <>
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="职位名称">
              <strong>{job.title || '-'}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="公司">
              {job.company || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="薪资">
              <Tag color="orange" style={{ fontWeight: 600 }}>
                {job.salary || '-'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="地区">
              {job.location || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="经验">
              {job.experience || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="学历">
              {job.education || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {job.is_active ? (
                <Tag color="success">活跃</Tag>
              ) : (
                <Tag color="default">已下架</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="首次发现">
              {job.first_seen_at ? new Date(job.first_seen_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="最后更新">
              {job.last_updated_at ? new Date(job.last_updated_at).toLocaleString('zh-CN') : '-'}
            </Descriptions.Item>
          </Descriptions>

          {job.url && (
            <div style={{ marginTop: 24 }}>
              <Button
                type="primary"
                icon={<ExternalLinkOutlined />}
                onClick={() => window.open(job.url!, '_blank')}
              >
                在 Boss 直聘查看
              </Button>
            </div>
          )}
        </>
      ) : (
        <div style={{ textAlign: 'center', color: '#64748b' }}>
          暂无数据
        </div>
      )}
    </Drawer>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/JobDrawer.tsx
git commit -m "feat(frontend): add JobDrawer component"
```

---

## Task 7: 创建职位表格组件

**Files:**
- Create: `frontend/src/components/JobList.tsx`

- [ ] **Step 1: 创建 JobList.tsx**

```typescript
import { useState } from 'react'
import {
  Table, Button, Space, Input, Select, Tag, Row, Col, Card,
} from 'antd'
import { RocketOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Job } from '@/types'

interface JobListProps {
  jobs: Job[] | undefined
  total: number
  isLoading: boolean
  onViewDetail: (job: Job) => void
  onCrawlAll: () => Promise<void>
  crawlAllLoading?: boolean
  // 筛选参数
  filters: {
    keyword: string
    is_active: boolean | undefined
  }
  onFilterChange: (filters: { keyword?: string; is_active?: boolean | undefined }) => void
  // 分页
  page: number
  pageSize: number
  onPageChange: (page: number) => void
}
```

修改 `useJobs` hook 接受过滤参数，删除客户端 filter 逻辑：

```typescript
// Job hooks - 修改签名
export const useJobs = (params?: {
  keyword?: string
  is_active?: boolean
  page?: number
  page_size?: number
}) => {
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: () => jobsApi.getJobs(params).then((res) => res.data),
    staleTime: 30_000,
  })
}
```

在 JobList 中连接筛选状态和分页：

```typescript
const handleKeywordChange = (value: string) => {
  onFilterChange({ keyword: value })
}

const handleStatusChange = (value: boolean | undefined) => {
  onFilterChange({ is_active: value })
}

return (
  <Card size="small" style={{ marginTop: 20 }}>
    <Row gutter={[8, 8]} align="middle" style={{ marginBottom: 16 }}>
      <Col flex="none">
        <Button type="primary" icon={<RocketOutlined />} onClick={onCrawlAll} loading={crawlAllLoading}>
          全部爬取
        </Button>
      </Col>
      <Col flex="auto">
        <Space>
          <Input
            placeholder="搜索职位/公司"
            allowClear
            style={{ width: 200 }}
            value={filters.keyword}
            onChange={(e) => handleKeywordChange(e.target.value)}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 100 }}
            value={filters.is_active}
            onChange={handleStatusChange}
            options={[
              { label: '活跃', value: true },
              { label: '下架', value: false },
            ]}
          />
        </Space>
      </Col>
    </Row>

    <Table
      rowKey="id"
      columns={columns}
      dataSource={jobs || []}
      loading={isLoading}
      pagination={{
        current: page,
        pageSize: pageSize,
        total: total,
        showTotal: (t) => `共 ${t} 条`,
        showSizeChanger: false,
        onChange: onPageChange,
      }}
      scroll={{ x: 1200 }}
    />
  </Card>
)

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/JobList.tsx
git commit -m "feat(frontend): add JobList component"
```

---

## Task 8: 创建主页面

**Files:**
- Create: `frontend/src/pages/JobsPage.tsx`

- [ ] **Step 1: 创建 JobsPage.tsx**

```typescript
import { useState } from 'react'
import { Card } from 'antd'
import {
  useJobConfigs,
  useCreateJobConfig,
  useUpdateJobConfig,
  useDeleteJobConfig,
  useJobs,
  useCrawlAllJobs,
  useCrawlSingleJob,
} from '@/hooks/api'
import JobConfigList from '@/components/JobConfigList'
import JobList from '@/components/JobList'
import JobDrawer from '@/components/JobDrawer'
import type { Job, JobSearchConfigCreate } from '@/types'

export default function JobsPage() {
  // 分页和筛选状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined)

  // Config hooks
  const { data: configs, isLoading: configsLoading, refetch: refetchConfigs } = useJobConfigs()
  const createConfig = useCreateJobConfig()
  const updateConfig = useUpdateJobConfig()
  const deleteConfig = useDeleteJobConfig()

  // Jobs hooks - 传入筛选参数
  const { data: jobs, isLoading: jobsLoading, refetch: refetchJobs } = useJobs({
    keyword: keyword || undefined,
    is_active: isActive,
    page,
    page_size: pageSize,
  })

  const crawlAll = useCrawlAllJobs()
  const crawlSingle = useCrawlSingleJob()

  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)

  // Handlers
  const handleCreateConfig = async (data: JobSearchConfigCreate) => {
    await createConfig.mutateAsync(data)
    await refetchConfigs()
  }

  const handleUpdateConfig = async (id: number, data: Partial<JobSearchConfigCreate>) => {
    await updateConfig.mutateAsync({ id, data })
    await refetchConfigs()
  }

  const handleDeleteConfig = async (id: number) => {
    await deleteConfig.mutateAsync(id)
    await refetchConfigs()
  }

  const handleCrawlSingle = async (id: number) => {
    await crawlSingle.mutateAsync(id)
    await refetchJobs()
    await refetchConfigs()
  }

  const handleCrawlAll = async () => {
    await crawlAll.mutateAsync()
    await refetchJobs()
    await refetchConfigs()
  }

  const handleViewDetail = (job: Job) => {
    setSelectedJob(job)
    setDrawerOpen(true)
  }

  const handleFilterChange = (filters: { keyword?: string; is_active?: boolean | undefined }) => {
    setPage(1) // 重置到第一页
    if (filters.keyword !== undefined) setKeyword(filters.keyword)
    if (filters.is_active !== undefined) setIsActive(filters.is_active)
  }

  return (
    <div>
      <Card size="small">
        <JobConfigList
          configs={configs}
          isLoading={configsLoading}
          onCreate={handleCreateConfig}
          onUpdate={handleUpdateConfig}
          onDelete={handleDeleteConfig}
          onCrawl={handleCrawlSingle}
          createLoading={createConfig.isPending}
          updateLoading={updateConfig.isPending}
          crawlLoading={crawlSingle.isPending}
        />
      </Card>

      <JobList
        jobs={jobs}
        total={jobs?.length || 0}  // TODO: 后端应返回 total 字段
        isLoading={jobsLoading}
        onViewDetail={handleViewDetail}
        onCrawlAll={handleCrawlAll}
        crawlAllLoading={crawlAll.isPending}
        filters={{ keyword, is_active: isActive }}
        onFilterChange={handleFilterChange}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
      />

      <JobDrawer
        open={drawerOpen}
        job={selectedJob}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
```

**注意:** 后端 `/jobs` API 当前返回 `Job[]`，没有 `total` 字段。需要修改后端 schema 添加分页响应：
- `total: int` - 总数
- `page: int` - 当前页
- `page_size: int` - 每页大小

或者接受前端用数组长度作为 total（不够精确但可工作）。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/JobsPage.tsx
git commit -m "feat(frontend): add JobsPage"
```

---

## Task 9: 添加路由和侧边栏菜单

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: 添加路由到 App.tsx**

在 `App.tsx` 中：
1. 添加 `import JobsPage from '@/pages/JobsPage'`
2. 在路由中添加 `<Route path="/jobs" element={<JobsPage />} />`
3. 在导航中添加 `<Route path="/jobs" element={<Navigate to="/jobs" replace />} />` （主页重定向）

```typescript
import JobsPage from '@/pages/JobsPage'

// 在 Routes 中添加
<Route path="/jobs" element={<JobsPage />} />
```

- [ ] **Step 2: 添加菜单到 AppLayout.tsx**

在菜单 items 中添加：

```typescript
import { TeamOutlined } from '@ant-design/icons'

// 在 useEffect 中添加
if (path.startsWith('/jobs')) setSelectedKey('/jobs')

// 在菜单 items 中添加
{
  key: '/jobs',
  icon: <TeamOutlined />,
  label: '职位管理',
},
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/App.tsx frontend/src/components/AppLayout.tsx
git commit -m "feat(frontend): add jobs route and menu"
```

| 修改 | `frontend/src/components/JobConfigList.tsx` | 添加 loading 状态简化和 Popconfirm |

---

## Task 10: 修复后端 API 分页响应

**Files:**
- Modify: `app/routers/jobs.py`
- Modify: `app/schemas/job.py`

- [ ] **Step 1: 添加 JobListResponse schema**

在 `app/schemas/job.py` 中添加：

```python
class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 2: 修改 list_jobs endpoint**

在 `app/routers/jobs.py` 的 `list_jobs` 函数中添加 count 查询：

```python
@router.get("", response_model=list[JobResponse])
async def list_jobs(...):
    # ... existing filter logic ...

    # 添加 count 查询
    count_query = select(func.count()).select_from(Job).join(JobSearchConfig).where(JobSearchConfig.user_id == 1)
    # ... apply filters to count_query ...
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    return result.scalars().all()
```

或者返回包含 total 的响应：

```python
@router.get("", response_model=JobListResponse)
async def list_jobs(...):
    # ... same filtering ...
    result = await db.execute(query)
    items = result.scalars().all()
    return JobListResponse(items=items, total=total, page=page, page_size=page_size)
```

- [ ] **Step 3: 提交**

```bash
git add app/routers/jobs.py app/schemas/job.py
git commit -m "feat(jobs): add pagination response with total count"
```

---

## Task 11: 验证

**Files:**
- None (verification only)

- [ ] **Step 1: 启动前端开发服务器**

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: 验证页面可访问**

在浏览器中访问 `http://localhost:5173/jobs`，应该看到职位管理页面。

- [ ] **Step 3: 验证功能**

1. 点击"新增配置"按钮，应该弹出表单
2. 创建配置后，应该看到配置卡片
3. 点击"爬取"按钮，应该触发爬取
4. 在职位列表中应该能看到职位数据
5. 点击"查看"按钮，应该弹出职位详情抽屉

- [ ] **Step 4: 提交最终版本**

```bash
git add -A
git commit -m "feat(frontend): complete boss zhipin job crawler frontend

- Add job config management (CRUD)
- Add job list with filtering and pagination
- Add job detail drawer
- Add manual crawl trigger
- Integrate with AppLayout and routing"
```