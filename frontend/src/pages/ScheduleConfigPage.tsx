import { useCallback, useEffect, useState } from 'react'
import { SaveOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Divider, Input, InputNumber, Modal, Select, Space, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useConfig, useUpdateConfig } from '@/hooks/api'
import { configApi } from '@/api/config'
import { jobsApi } from '@/api/jobs'
import { productsApi } from '@/api/products'
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
  taobao: '淘宝',
  jd: '京东',
  amazon: '亚马逊',
}

export default function ScheduleConfigPage() {
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
      message.error('加载商品定时配置失败')
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
      message.error('加载职位定时配置失败')
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
      message.success('保留天数已保存')
      refetch()
    } catch {
      message.error('保存失败')
    }
  }

  const handleSaveWebhook = async () => {
    try {
      await updateMutation.mutateAsync({ feishu_webhook_url: feishuWebhookUrl })
      message.success('Webhook URL 已保存')
      refetch()
    } catch {
      message.error('保存失败')
    }
  }

  const handleAddPlatformCron = async () => {
    if (!addPlatform) {
      message.error('请选择平台')
      return
    }
    const value = addCron.trim() || null
    if (value && !isValidCronFormat(value)) {
      message.error('Cron 表达式不合法')
      return
    }
    setAddSaving(true)
    try {
      await productsApi.createCronConfig({
        platform: addPlatform,
        cron_expression: value,
        cron_timezone: 'Asia/Shanghai',
      })
      message.success('已添加')
      setAddModalOpen(false)
      setAddPlatform(undefined)
      setAddCron('')
      void loadPlatformData()
    } catch {
      message.error('添加失败')
    } finally {
      setAddSaving(false)
    }
  }

  const handleDeletePlatformCron = async (platform: string) => {
    Modal.confirm({
      title: '删除定时配置',
      content: `确定删除 ${PLATFORM_LABELS[platform] || platform} 的定时配置？`,
      onOk: async () => {
        try {
          await productsApi.deleteCronConfig(platform)
          message.success('已删除')
          void loadPlatformData()
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const handleSavePlatformCron = async (platform: string) => {
    const value = platformCronInputs[platform]?.trim() || null
    if (value && !isValidCronFormat(value)) {
      message.error('Cron 表达式不合法')
      return
    }
    setPlatformSaving((prev) => ({ ...prev, [platform]: true }))
    try {
      await productsApi.updateCronConfig(platform, {
        cron_expression: value,
        cron_timezone: 'Asia/Shanghai',
      })
      message.success('已保存')
      void loadPlatformData()
    } catch {
      message.error('保存失败')
    } finally {
      setPlatformSaving((prev) => ({ ...prev, [platform]: false }))
    }
  }

  const handleSaveConfigCron = async (configId: number) => {
    const value = cronInputs[configId]?.trim() || null
    if (value && !isValidCronFormat(value)) {
      message.error('Cron 表达式不合法')
      return
    }
    setSavingCron((prev) => ({ ...prev, [configId]: true }))
    try {
      await jobsApi.updateConfigCron(configId, {
        cron_expression: value,
        cron_timezone: 'Asia/Shanghai',
      })
      message.success('已保存')
      void loadConfigData()
    } catch {
      message.error('保存失败')
    } finally {
      setSavingCron((prev) => ({ ...prev, [configId]: false }))
    }
  }

  const platformColumns: ColumnsType<ProductPlatformCron> = [
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      width: 120,
      render: (value: string) => PLATFORM_LABELS[value] || value,
    },
    {
      title: 'Cron 表达式',
      key: 'cron',
      width: 340,
      render: (_, record) => (
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={platformCronInputs[record.platform] ?? ''}
            onChange={(e) =>
              setPlatformCronInputs((prev) => ({ ...prev, [record.platform]: e.target.value }))
            }
            placeholder="0 9 * * *"
            style={{ width: 220 }}
          />
          <Button
            type="primary"
            onClick={() => void handleSavePlatformCron(record.platform)}
            loading={platformSaving[record.platform]}
          >
            保存
          </Button>
        </Space.Compact>
      ),
    },
    {
      title: '下次执行',
      key: 'next_run',
      width: 200,
      render: (_, record) => {
        const schedule = platformSchedules[record.platform]
        return schedule?.next_run_at ? new Date(schedule.next_run_at).toLocaleString('zh-CN') : <Tag>未调度</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 90,
      render: (_, record) => (
        <Button danger size="small" onClick={() => void handleDeletePlatformCron(record.platform)}>
          删除
        </Button>
      ),
    },
  ]

  const configColumns: ColumnsType<JobSearchConfig> = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      width: 160,
      ellipsis: true,
    },
    {
      title: 'Cron 表达式',
      key: 'cron',
      width: 340,
      render: (_, record) => (
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={cronInputs[record.id] ?? ''}
            onChange={(e) => setCronInputs((prev) => ({ ...prev, [record.id]: e.target.value }))}
            placeholder="0 9 * * *"
            style={{ width: 220 }}
          />
          <Button
            type="primary"
            onClick={() => void handleSaveConfigCron(record.id)}
            loading={savingCron[record.id]}
          >
            保存
          </Button>
        </Space.Compact>
      ),
    },
    {
      title: '下次执行',
      key: 'next_run',
      width: 200,
      render: (_, record) => {
        const schedule = configSchedules[record.id]
        return schedule?.next_run_at ? new Date(schedule.next_run_at).toLocaleString('zh-CN') : <Tag>未调度</Tag>
      },
    },
  ]

  return (
    <div>
      <h1 style={{ fontSize: 24, color: '#1f2937', marginBottom: 24, fontWeight: 500 }}>定时配置</h1>

      {isError && !isLoading && (
        <Alert
          type="error"
          message="加载失败"
          description="无法获取配置，请稍后重试。"
          action={
            <Button size="small" onClick={() => void refetch()}>
              重试
            </Button>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      <Card title="Cron 定时配置" style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h4 style={{ margin: 0, color: '#1f2937' }}>商品抓取定时配置</h4>
          <Button type="primary" size="small" onClick={() => setAddModalOpen(true)}>
            新增定时器
          </Button>
        </div>
        <Table
          dataSource={platformConfigs}
          columns={platformColumns}
          rowKey="platform"
          loading={platformLoading}
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无商品定时配置' }}
        />

        <Divider style={{ margin: '16px 0' }} />

        <h4 style={{ marginBottom: 12, color: '#1f2937' }}>职位抓取定时配置</h4>
        <Table
          dataSource={configList}
          columns={configColumns}
          rowKey="id"
          loading={configLoading}
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无职位搜索配置' }}
        />
      </Card>

      <Card title="数据保留与通知配置" style={{ marginTop: 24 }}>
        <div style={{ marginBottom: 20 }}>
          <div style={{ marginBottom: 4, color: '#666' }}>飞书 Webhook URL</div>
          <Space.Compact style={{ width: '100%', maxWidth: 560 }}>
            <Input
              value={feishuWebhookUrl}
              onChange={(e) => setFeishuWebhookUrl(e.target.value)}
              placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
            />
            <Button type="primary" onClick={() => void handleSaveWebhook()} loading={updateMutation.isPending}>
              保存
            </Button>
          </Space.Compact>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: '#666', whiteSpace: 'nowrap' }}>数据保留天数</span>
          <Space.Compact>
            <InputNumber min={1} max={3650} value={retentionDays} onChange={(v) => setRetentionDays(v ?? 365)} style={{ width: 160 }} />
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => void handleSaveRetention()}
              loading={updateMutation.isPending}
            >
              保存
            </Button>
          </Space.Compact>
        </div>
      </Card>

      <Modal
        title="新增商品抓取定时器"
        open={addModalOpen}
        onOk={() => void handleAddPlatformCron()}
        onCancel={() => {
          setAddModalOpen(false)
          setAddPlatform(undefined)
          setAddCron('')
        }}
        confirmLoading={addSaving}
        okText="添加"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
          <div>
            <div style={{ marginBottom: 4, color: '#666' }}>平台</div>
            <Select
              value={addPlatform}
              onChange={setAddPlatform}
              placeholder="选择平台"
              style={{ width: '100%' }}
              options={[
                { value: 'taobao', label: '淘宝' },
                { value: 'jd', label: '京东' },
                { value: 'amazon', label: '亚马逊' },
              ]}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, color: '#666' }}>Cron 表达式</div>
            <Input value={addCron} onChange={(e) => setAddCron(e.target.value)} placeholder="0 9 * * *" />
          </div>
        </div>
      </Modal>
    </div>
  )
}
