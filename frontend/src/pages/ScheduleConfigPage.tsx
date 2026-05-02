import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Divider,
  Input,
  InputNumber,
  Skeleton,
  Space,
  Table,
  Tag,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { SaveOutlined } from '@ant-design/icons'
import { useConfig, useUpdateConfig } from '@/hooks/api'
import { configApi } from '@/api/config'
import { jobsApi } from '@/api/jobs'
import { productsApi } from '@/api/products'
import type {
  JobConfigScheduleInfo,
  JobSearchConfig,
  ProductPlatformCron,
  ProductPlatformCronSchedule,
  SchedulerJobStatus,
} from '@/types'

const CRON_SEGMENT_RE = /^(\*|[0-9]+(?:-[0-9]+)?(?:\/[0-9]+)?)$/

const isValidCronFormat = (value: string): boolean => {
  const parts = value.trim().split(/\s+/)
  if (parts.length !== 5) return false
  return parts.every((part) => CRON_SEGMENT_RE.test(part))
}

const PLATFORM_LABELS: Record<string, string> = {
  taobao: '淘宝',
  jd: '京东',
  amazon: '亚马逊',
}

export default function ScheduleConfigPage() {
  const { data: config, isLoading, isError, refetch } = useConfig()
  const updateMutation = useUpdateConfig()

  // Data retention state
  const [retentionDays, setRetentionDays] = useState(365)

  // Product platform cron management
  const [platformConfigs, setPlatformConfigs] = useState<ProductPlatformCron[]>([])
  const [platformSchedules, setPlatformSchedules] = useState<
    Record<string, ProductPlatformCronSchedule>
  >({})
  const [platformLoading, setPlatformLoading] = useState(false)
  const [platformCronInputs, setPlatformCronInputs] = useState<Record<string, string>>({})
  const [platformSaving, setPlatformSaving] = useState<Record<string, boolean>>({})

  // Job per-config cron management
  const [configList, setConfigList] = useState<JobSearchConfig[]>([])
  const [configSchedules, setConfigSchedules] = useState<Record<number, JobConfigScheduleInfo>>({})
  const [configLoading, setConfigLoading] = useState(false)
  const [cronInputs, setCronInputs] = useState<Record<number, string>>({})
  const [savingCron, setSavingCron] = useState<Record<number, boolean>>({})

  // Scheduler status
  const [schedulerJobs, setSchedulerJobs] = useState<Record<string, SchedulerJobStatus>>({})
  const [schedulerLoading, setSchedulerLoading] = useState(true)
  const [schedulerError, setSchedulerError] = useState(false)

  const fetchSchedulerStatus = useCallback(async () => {
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
  }, [])

  // Load product platform cron configs
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
      for (const c of configs) {
        inputs[c.platform] = c.cron_expression || ''
      }
      setPlatformCronInputs(inputs)
    } catch {
      message.error('加载商品定时配置失败')
    } finally {
      setPlatformLoading(false)
    }
  }, [])

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
      loadPlatformData()
    } catch {
      message.error('保存失败')
    } finally {
      setPlatformSaving((prev) => ({ ...prev, [platform]: false }))
    }
  }

  // Load job config cron data
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
      for (const s of schedulesRes.data.configs) {
        scheduleMap[s.config_id] = s
      }
      setConfigSchedules(scheduleMap)
      const inputs: Record<number, string> = {}
      for (const c of configs) {
        inputs[c.id] = c.cron_expression || ''
      }
      setCronInputs(inputs)
    } catch {
      message.error('加载职位配置列表失败')
    } finally {
      setConfigLoading(false)
    }
  }, [])

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
      loadConfigData()
    } catch {
      message.error('保存失败')
    } finally {
      setSavingCron((prev) => ({ ...prev, [configId]: false }))
    }
  }

  // Init retention from config and fetch all data on mount
  useEffect(() => {
    if (config) {
      setRetentionDays(config.data_retention_days || 365)
    }
  }, [config])

  useEffect(() => {
    fetchSchedulerStatus()
    loadPlatformData()
    loadConfigData()
  }, [fetchSchedulerStatus, loadPlatformData, loadConfigData])

  const handleSaveRetention = async () => {
    try {
      await updateMutation.mutateAsync({ data_retention_days: retentionDays })
      message.success('配置已保存')
      refetch()
    } catch {
      message.error('保存失败')
    }
  }

  // Product platform cron columns
  const platformColumns: ColumnsType<ProductPlatformCron> = [
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      width: 120,
      render: (p: string) => PLATFORM_LABELS[p] || p,
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
            placeholder="0 9 * * *（空=不定时）"
            style={{ width: 220 }}
          />
          <Button
            type="primary"
            onClick={() => handleSavePlatformCron(record.platform)}
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
        if (!schedule?.next_run_at) return <Tag>未调度</Tag>
        return new Date(schedule.next_run_at).toLocaleString('zh-CN')
      },
    },
  ]

  // Job config cron columns
  const configColumns: ColumnsType<JobSearchConfig> = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: 'Cron 表达式',
      key: 'cron',
      width: 340,
      render: (_, record) => (
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={cronInputs[record.id] ?? ''}
            onChange={(e) =>
              setCronInputs((prev) => ({ ...prev, [record.id]: e.target.value }))
            }
            placeholder="0 9 * * *（空=不定时）"
            style={{ width: 220 }}
          />
          <Button
            type="primary"
            onClick={() => handleSaveConfigCron(record.id)}
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
        if (!schedule?.next_run_at) return <Tag>未调度</Tag>
        return new Date(schedule.next_run_at).toLocaleString('zh-CN')
      },
    },
  ]

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

      <Card title="Cron 定时配置" style={{ marginTop: 24 }}>
        <h4 style={{ marginBottom: 12, color: '#1f2937' }}>商品爬取定时配置</h4>
        <Table
          dataSource={platformConfigs}
          columns={platformColumns}
          rowKey="platform"
          loading={platformLoading}
          pagination={false}
          size="small"
          locale={{ emptyText: '加载中...' }}
        />

        <Divider style={{ margin: '16px 0' }} />

        <h4 style={{ marginBottom: 12, color: '#1f2937' }}>职位爬取定时配置</h4>
        <Table
          dataSource={configList}
          columns={configColumns}
          rowKey="id"
          loading={configLoading}
          pagination={false}
          size="small"
          locale={{ emptyText: '暂无搜索配置' }}
        />
      </Card>

      <Card title="数据保留与其他配置" style={{ marginTop: 24 }}>
        <Space.Compact style={{ width: '100%', maxWidth: 300 }}>
          <InputNumber
            min={1}
            max={3650}
            value={retentionDays}
            onChange={(v) => setRetentionDays(v ?? 365)}
            addonAfter="天"
            style={{ width: '100%' }}
          />
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSaveRetention}
            loading={updateMutation.isPending}
          >
            保存配置
          </Button>
        </Space.Compact>
      </Card>
    </div>
  )
}
