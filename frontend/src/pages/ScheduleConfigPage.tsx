import { useCallback, useEffect, useState } from 'react'
import { DeleteOutlined, SaveOutlined } from '@ant-design/icons'
import { Alert, App, Button, Divider, Input, InputNumber, Modal, Select, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useConfig, useUpdateConfig } from '@/hooks/api'
import { configApi } from '@/api/config'
import { jobsApi } from '@/api/jobs'
import { productsApi } from '@/api/products'
import { useAuth } from '@/contexts/AuthContext'
import type {
  JobConfigScheduleInfo,
  JobSearchConfig,
  ProductPlatformCron,
  ProductPlatformCronSchedule,
} from '@/types'

const CRON_SEGMENT_RE = /^(\*|[0-9]+(?:-[0-9]+)?(?:\/[0-9]+)?)$/

const isValidCronFormat = (value: string): boolean => {
  const parts = value.trim().split(/\s+/)
  return parts.length === 5 && parts.every((part) => CRON_SEGMENT_RE.test(part))
}

const PLATFORM_LABELS: Record<string, string> = {
  taobao: 'Taobao',
  jd: 'JD',
  amazon: 'Amazon',
}

export default function ScheduleConfigPage() {
  const { user } = useAuth()
  const isReadOnly = user?.role === 'admin'
  const message = App.useApp().message
  const { data: config, isLoading, isError, refetch } = useConfig()
  const updateMutation = useUpdateConfig()

  const [retentionDays, setRetentionDays] = useState(365)
  const [feishuWebhookUrl, setFeishuWebhookUrl] = useState('')

  const [platformConfigs, setPlatformConfigs] = useState<ProductPlatformCron[]>([])
  const [platformSchedules, setPlatformSchedules] = useState<Record<string, ProductPlatformCronSchedule>>({})
  const [platformLoading, setPlatformLoading] = useState(false)
  const [platformCronInputs, setPlatformCronInputs] = useState<Record<string, string>>({})
  const [platformSaving, setPlatformSaving] = useState<Record<string, boolean>>({})

  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addPlatform, setAddPlatform] = useState<string | undefined>(undefined)
  const [addCron, setAddCron] = useState('')
  const [addSaving, setAddSaving] = useState(false)

  const [configList, setConfigList] = useState<JobSearchConfig[]>([])
  const [configSchedules, setConfigSchedules] = useState<Record<number, JobConfigScheduleInfo>>({})
  const [configLoading, setConfigLoading] = useState(false)
  const [cronInputs, setCronInputs] = useState<Record<number, string>>({})
  const [savingCron, setSavingCron] = useState<Record<number, boolean>>({})

  const fetchSchedulerStatus = useCallback(async () => {
    try {
      await configApi.getSchedulerStatus()
    } catch {
      // page uses per-table schedule endpoints directly; ignore status failures
    }
  }, [])

  const loadPlatformData = useCallback(async () => {
    setPlatformLoading(true)
    try {
      const [configsRes, schedulesRes] = await Promise.all([
        productsApi.getCronConfigs(),
        productsApi.getCronSchedules(),
      ])
      const configs = configsRes.data
      setPlatformConfigs(configs)
      setPlatformSchedules(schedulesRes.data.platforms)
      const inputs: Record<string, string> = {}
      configs.forEach((configItem) => {
        inputs[configItem.platform] = configItem.cron_expression || ''
      })
      setPlatformCronInputs(inputs)
    } catch {
      message.error('Failed to load product schedule config')
    } finally {
      setPlatformLoading(false)
    }
  }, [])

  const loadConfigData = useCallback(async () => {
    setConfigLoading(true)
    try {
      const [configsRes, schedulesRes] = await Promise.all([
        jobsApi.getConfigs(),
        jobsApi.getJobConfigSchedules(),
      ])
      const configs = configsRes.data
      setConfigList(configs)
      const scheduleMap: Record<number, JobConfigScheduleInfo> = {}
      schedulesRes.data.configs.forEach((item) => {
        scheduleMap[item.config_id] = item
      })
      setConfigSchedules(scheduleMap)
      const inputs: Record<number, string> = {}
      configs.forEach((configItem) => {
        inputs[configItem.id] = configItem.cron_expression || ''
      })
      setCronInputs(inputs)
    } catch {
      message.error('Failed to load job schedule config')
    } finally {
      setConfigLoading(false)
    }
  }, [])

  useEffect(() => {
    if (config) {
      setRetentionDays(config.data_retention_days || 365)
      setFeishuWebhookUrl(config.feishu_webhook_url || '')
    }
  }, [config])

  useEffect(() => {
    void fetchSchedulerStatus()
    void loadPlatformData()
    void loadConfigData()
  }, [fetchSchedulerStatus, loadPlatformData, loadConfigData])

  const handleSaveRetention = async () => {
    try {
      await updateMutation.mutateAsync({ data_retention_days: retentionDays })
      message.success('Retention days saved')
      refetch()
    } catch {
      message.error('Save failed')
    }
  }

  const handleSaveWebhook = async () => {
    try {
      await updateMutation.mutateAsync({ feishu_webhook_url: feishuWebhookUrl })
      message.success('Webhook URL saved')
      refetch()
    } catch {
      message.error('Save failed')
    }
  }

  const handleAddPlatformCron = async () => {
    if (!addPlatform) {
      message.error('Please select a platform')
      return
    }
    const value = addCron.trim() || null
    if (value && !isValidCronFormat(value)) {
      message.error('Invalid cron expression')
      return
    }
    setAddSaving(true)
    try {
      await productsApi.createCronConfig({
        platform: addPlatform,
        cron_expression: value,
        cron_timezone: 'Asia/Shanghai',
      })
      message.success('Added')
      setAddModalOpen(false)
      setAddPlatform(undefined)
      setAddCron('')
      void loadPlatformData()
    } catch {
      message.error('Add failed')
    } finally {
      setAddSaving(false)
    }
  }

  const handleDeletePlatformCron = async (platform: string) => {
    Modal.confirm({
      title: 'Delete Schedule Config',
      content: `Delete schedule config for ${PLATFORM_LABELS[platform] || platform}?`,
      onOk: async () => {
        try {
          await productsApi.deleteCronConfig(platform)
          message.success('Deleted')
          void loadPlatformData()
        } catch {
          message.error('Delete failed')
        }
      },
    })
  }

  const handleSavePlatformCron = async (platform: string) => {
    const value = platformCronInputs[platform]?.trim() || null
    if (value && !isValidCronFormat(value)) {
      message.error('Invalid cron expression')
      return
    }
    setPlatformSaving((prev) => ({ ...prev, [platform]: true }))
    try {
      await productsApi.updateCronConfig(platform, {
        cron_expression: value,
        cron_timezone: 'Asia/Shanghai',
      })
      message.success('Saved')
      void loadPlatformData()
    } catch {
      message.error('Save failed')
    } finally {
      setPlatformSaving((prev) => ({ ...prev, [platform]: false }))
    }
  }

  const handleSaveConfigCron = async (configId: number) => {
    const value = cronInputs[configId]?.trim() || null
    if (value && !isValidCronFormat(value)) {
      message.error('Invalid cron expression')
      return
    }
    setSavingCron((prev) => ({ ...prev, [configId]: true }))
    try {
      await jobsApi.updateConfigCron(configId, {
        cron_expression: value,
        cron_timezone: 'Asia/Shanghai',
      })
      message.success('Saved')
      void loadConfigData()
    } catch {
      message.error('Save failed')
    } finally {
      setSavingCron((prev) => ({ ...prev, [configId]: false }))
    }
  }

  const platformColumns: ColumnsType<ProductPlatformCron> = [
    {
      title: 'Platform',
      dataIndex: 'platform',
      key: 'platform',
      width: 200,
      render: (value: string) => PLATFORM_LABELS[value] || value,
    },
    {
      title: 'Cron Expression',
      key: 'cron',
      width: 450,
      render: (_: unknown, record: ProductPlatformCron) => (
        <Space>
          <Input
            value={platformCronInputs[record.platform] ?? ''}
            onChange={(e) =>
              setPlatformCronInputs((prev) => ({ ...prev, [record.platform]: e.target.value }))
            }
            placeholder="0 9 * * *"
            style={{ width: 220 }}
            disabled={isReadOnly}
          />
          <Button
            onClick={() => void handleSavePlatformCron(record.platform)}
            loading={platformSaving[record.platform]}
            disabled={isReadOnly}
            className="fg-btn-secondary"
          >
            Save
          </Button>
        </Space>
      ),
    },
    {
      title: 'Next Run',
      key: 'next_run',
      render: (_, record) => {
        const schedule = platformSchedules[record.platform]
        const nextRun = schedule?.next_run_at
          ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(schedule.next_run_at))
          : null
        return nextRun ? nextRun : <Tag>Unscheduled</Tag>
      },
    },
    ...(isReadOnly
      ? []
      : [
          {
            title: 'Actions',
            key: 'action',
            width: 90,
            render: (_: unknown, record: ProductPlatformCron) => (
              <Button danger size="small" icon={<DeleteOutlined />} onClick={() => void handleDeletePlatformCron(record.platform)}>
                Delete
              </Button>
            ),
          },
        ]),
  ] as ColumnsType<ProductPlatformCron>

  const configColumns: ColumnsType<JobSearchConfig> = [
    {
      title: 'Config Name',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Cron Expression',
      key: 'cron',
      width: 450,
      render: (_, record) => (
        <Space>
          <Input
            value={cronInputs[record.id] ?? ''}
            onChange={(e) => setCronInputs((prev) => ({ ...prev, [record.id]: e.target.value }))}
            placeholder="0 9 * * *"
            style={{ width: 220 }}
            disabled={isReadOnly}
          />
          <Button
            onClick={() => void handleSaveConfigCron(record.id)}
            loading={savingCron[record.id]}
            disabled={isReadOnly}
            className="fg-btn-secondary"
          >
            Save
          </Button>
        </Space>
      ),
    },
    {
      title: 'Next Run',
      key: 'next_run',
      render: (_, record) => {
        const schedule = configSchedules[record.id]
        const nextRun = schedule?.next_run_at
          ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(schedule.next_run_at))
          : null
        return nextRun ? nextRun : <Tag>Unscheduled</Tag>
      },
    },
  ]

  return (
    <div>
      {/* Page header — mint color block (DESIGN.md: Mint — 配置) */}
      <div className="page-header bg-mint">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">Automation</p>
            <h1 className="page-title">Schedule Config</h1>
            <p className="page-subtitle">Configure product and job crawl schedules and notification channels</p>
          </div>
        </div>
      </div>

      {isReadOnly && (
        <Alert
          type="warning"
          message="Read-only Mode"
          description="Admin accounts cannot modify schedule configs. Please contact the system administrator."
          style={{ marginBottom: 24 }}
          showIcon
        />
      )}

      {isError && !isLoading && (
        <Alert
          type="error"
          message="Load Failed"
          description="Unable to fetch configuration. Please try again later."
          action={
            <Button size="small" onClick={() => void refetch()} className="fg-btn-secondary fg-btn-sm">
              Retry
            </Button>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Cron config card */}
      <div className="fg-card" style={{ marginTop: 24 }}>
        <div className="fg-card-header">
          <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
            Cron Schedule Configuration
          </span>
        </div>
        <div style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '0 0 12px' }}>
            <h4 style={{ fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 480, color: 'var(--color-ink)', margin: 0 }}>
              Product Crawl Schedule Config
            </h4>
            {!isReadOnly && (
              <Button
                size="small"
                onClick={() => setAddModalOpen(true)}
                className="fg-btn-secondary fg-btn-sm"
              >
                Add Product Timer
              </Button>
            )}
          </div>
          <Table
            dataSource={platformConfigs}
            columns={platformColumns}
            rowKey="platform"
            loading={platformLoading}
            pagination={false}
            size="small"
            scroll={{ x: 1000 }}
            locale={{ emptyText: 'No product schedule configs' }}
          />

          <Divider style={{ margin: '16px 0' }} />

          <h4 style={{ fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 480, color: 'var(--color-ink)', margin: '0 0 12px' }}>
            Job Crawl Schedule Config
          </h4>
          <Table
            dataSource={configList}
            columns={configColumns}
            rowKey="id"
            loading={configLoading}
            pagination={false}
            size="small"
            scroll={{ x: 1000 }}
            locale={{ emptyText: 'No job search configs' }}
          />
        </div>
      </div>

      {/* Data & notification card */}
      <div className="fg-card" style={{ marginTop: 16 }}>
        <div className="fg-card-header">
          <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
            Data Retention & Notification Config
          </span>
        </div>
        <div style={{ padding: '20px 24px' }}>
          <div style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 6, fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 330, color: 'var(--color-muted)' }}>
              Feishu Webhook URL
            </div>
            <Space>
              <Input
                value={feishuWebhookUrl}
                onChange={(e) => setFeishuWebhookUrl(e.target.value)}
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                autoComplete="off"
                style={{ width: 420, fontFamily: 'var(--font-body)', fontSize: 14 }}
              />
              <Button
                onClick={() => void handleSaveWebhook()}
                loading={updateMutation.isPending}
                disabled={isReadOnly}
                className="fg-btn-secondary"
              >
                Save
              </Button>
            </Space>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 330, color: 'var(--color-muted)', whiteSpace: 'nowrap' }}>
              Data Retention Days
            </span>
            <Space>
              <InputNumber
                min={1}
                max={3650}
                value={retentionDays}
                onChange={(v) => setRetentionDays(v ?? 365)}
                style={{ width: 160, fontFamily: 'var(--font-body)' }}
                disabled={isReadOnly}
              />
              <Button
                icon={<SaveOutlined style={{ fontSize: 13 }} />}
                onClick={() => void handleSaveRetention()}
                loading={updateMutation.isPending}
                disabled={isReadOnly}
                className="fg-btn-secondary"
              >
                Save
              </Button>
            </Space>
          </div>
        </div>
      </div>

      <Modal
        title="Add Product Crawl Timer"
        open={addModalOpen}
        onOk={() => void handleAddPlatformCron()}
        onCancel={() => {
          setAddModalOpen(false)
          setAddPlatform(undefined)
          setAddCron('')
        }}
        confirmLoading={addSaving}
        okText="Add"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
          <div>
            <div style={{ marginBottom: 4, fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 330, color: 'var(--color-muted)' }}>
              Platform
            </div>
            <Select
              value={addPlatform}
              onChange={setAddPlatform}
              placeholder="Select platform"
              style={{ width: '100%', fontFamily: 'var(--font-body)' }}
              options={[
                { value: 'taobao', label: 'Taobao' },
                { value: 'jd', label: 'JD' },
                { value: 'amazon', label: 'Amazon' },
              ]}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: 330, color: 'var(--color-muted)' }}>
              Cron Expression
            </div>
            <Input
              value={addCron}
              onChange={(e) => setAddCron(e.target.value)}
              placeholder="0 9 * * *"
              style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 14 }}
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
