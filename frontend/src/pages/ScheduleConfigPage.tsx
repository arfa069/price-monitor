import { useCallback, useEffect, useState } from 'react'
import { SaveOutlined } from '@ant-design/icons'
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
  taobao: '淘宝',
  jd: '京东',
  amazon: '亚马逊',
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
      width: 160,
      ellipsis: true,
      render: (value: string) => PLATFORM_LABELS[value] || value,
    },
    {
      title: 'Cron 表达式',
      key: 'cron',
      width: 340,
      render: (_: unknown, record: ProductPlatformCron) => (
        <Space.Compact style={{ width: '100%' }}>
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
            type="primary"
            onClick={() => void handleSavePlatformCron(record.platform)}
            loading={platformSaving[record.platform]}
            disabled={isReadOnly}
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
        const nextRun = schedule?.next_run_at
          ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(schedule.next_run_at))
          : null
        return nextRun ? nextRun : <Tag>未调度</Tag>
      },
    },
    ...(isReadOnly
      ? []
      : [
          {
            title: '操作',
            key: 'action',
            width: 90,
            render: (_: unknown, record: ProductPlatformCron) => (
              <Button danger size="small" onClick={() => void handleDeletePlatformCron(record.platform)}>
                删除
              </Button>
            ),
          },
        ]),
  ] as ColumnsType<ProductPlatformCron>

  const configColumns: ColumnsType<JobSearchConfig> = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
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
            disabled={isReadOnly}
          />
          <Button
            type="primary"
            onClick={() => void handleSaveConfigCron(record.id)}
            loading={savingCron[record.id]}
            disabled={isReadOnly}
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
        const nextRun = schedule?.next_run_at
          ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(schedule.next_run_at))
          : null
        return nextRun ? nextRun : <Tag>未调度</Tag>
      },
    },
  ]

  return (
    <div>
      {/* Page header — lime color block */}
      <div className="page-header bg-lime">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">自动化</p>
            <h1 className="page-title">定时配置</h1>
            <p className="page-subtitle">配置商品和职位的定时爬取计划与通知渠道</p>
          </div>
        </div>
      </div>

      {isReadOnly && (
        <Alert
          type="warning"
          message="只读模式"
          description="管理员账号无权修改定时配置，请联系系统管理员。"
          style={{ marginBottom: 24 }}
          showIcon
        />
      )}

      {isError && !isLoading && (
        <Alert
          type="error"
          message="加载失败"
          description="无法获取配置，请稍后重试。"
          action={
            <Button size="small" onClick={() => void refetch()} className="fg-btn-secondary fg-btn-sm">
              重试
            </Button>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Cron config card */}
      <div className="fg-card" style={{ marginTop: 24 }}>
        <div className="fg-card-header">
          <span style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 15, fontWeight: 480, color: '#000' }}>
            Cron 定时配置
          </span>
        </div>
        <div style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '0 0 12px' }}>
            <h4 style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14, fontWeight: 480, color: '#000', margin: 0 }}>
              商品抓取定时配置
            </h4>
            {!isReadOnly && (
              <Button
                type="primary"
                size="small"
                onClick={() => setAddModalOpen(true)}
                className="fg-btn-primary fg-btn-sm"
              >
                新增商品定时器
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
            locale={{ emptyText: '暂无商品定时配置' }}
          />

          <Divider style={{ margin: '16px 0' }} />

          <h4 style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14, fontWeight: 480, color: '#000', margin: '0 0 12px' }}>
            职位抓取定时配置
          </h4>
          <Table
            dataSource={configList}
            columns={configColumns}
            rowKey="id"
            loading={configLoading}
            pagination={false}
            size="small"
            locale={{ emptyText: '暂无职位搜索配置' }}
          />
        </div>
      </div>

      {/* Data & notification card */}
      <div className="fg-card" style={{ marginTop: 16 }}>
        <div className="fg-card-header">
          <span style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 15, fontWeight: 480, color: '#000' }}>
            数据保留与通知配置
          </span>
        </div>
        <div style={{ padding: '20px 24px' }}>
          <div style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 6, fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14, fontWeight: 330, color: '#666' }}>
              飞书 Webhook URL
            </div>
            <Space.Compact style={{ width: '100%', maxWidth: 560 }}>
              <Input
                value={feishuWebhookUrl}
                onChange={(e) => setFeishuWebhookUrl(e.target.value)}
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14 }}
              />
              <Button
                type="primary"
                onClick={() => void handleSaveWebhook()}
                loading={updateMutation.isPending}
                disabled={isReadOnly}
                className="fg-btn-primary"
              >
                保存
              </Button>
            </Space.Compact>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14, fontWeight: 330, color: '#666', whiteSpace: 'nowrap' }}>
              数据保留天数
            </span>
            <Space.Compact>
              <InputNumber
                min={1}
                max={3650}
                value={retentionDays}
                onChange={(v) => setRetentionDays(v ?? 365)}
                style={{ width: 160, fontFamily: "'Inter', system-ui, sans-serif" }}
                disabled={isReadOnly}
              />
              <Button
                type="primary"
                icon={<SaveOutlined style={{ fontSize: 13 }} />}
                onClick={() => void handleSaveRetention()}
                loading={updateMutation.isPending}
                disabled={isReadOnly}
                className="fg-btn-primary"
              >
                保存
              </Button>
            </Space.Compact>
          </div>
        </div>
      </div>

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
            <div style={{ marginBottom: 4, fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14, fontWeight: 330, color: '#666' }}>
              平台
            </div>
            <Select
              value={addPlatform}
              onChange={setAddPlatform}
              placeholder="选择平台"
              style={{ width: '100%', fontFamily: "'Inter', system-ui, sans-serif" }}
              options={[
                { value: 'taobao', label: '淘宝' },
                { value: 'jd', label: '京东' },
                { value: 'amazon', label: '亚马逊' },
              ]}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4, fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14, fontWeight: 330, color: '#666' }}>
              Cron 表达式
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
