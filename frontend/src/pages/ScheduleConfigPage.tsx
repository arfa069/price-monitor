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
  Tag,
  message,
} from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import { useConfig, useUpdateConfig } from '@/hooks/api'
import { configApi } from '@/api/config'
import type { SchedulerJobStatus } from '@/types'

type ScheduleMode = 'hours' | 'cron'

const CRON_SEGMENT_RE = /^(\*|[0-9]+(?:-[0-9]+)?(?:\/[0-9]+)?)$/

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

export default function ScheduleConfigPage() {
  const { data: config, isLoading, isError, refetch } = useConfig()
  const updateMutation = useUpdateConfig()
  const [form] = Form.useForm<ScheduleFormValues>()

  // Cron card state
  const [productCron, setProductCron] = useState('')
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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing external config into local state
    setProductCron(config.crawl_cron || '')
    setJobCron(config.job_crawl_cron || '')
  }, [config, form])

  // Fetch scheduler status on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch on mount
    fetchSchedulerStatus()
  }, [])

  const scheduleMode =
    Form.useWatch('schedule_mode', form) ?? (config?.crawl_cron ? 'cron' : 'hours')
  const cronValid = useMemo(
    () => (productCron.trim() ? isValidCronFormat(productCron) : null),
    [productCron],
  )

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
      await configApi.update({ crawl_cron: productCron.trim(), crawl_timezone: 'Asia/Shanghai' })
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

            {scheduleMode === 'cron' && null}
          </Card>
        )}
      </Form>

      <Card
        title="Cron 定时配置"
        extra={scheduleMode === 'cron' ? <Tag color="blue">Cron 模式已启用</Tag> : null}
        style={{ marginTop: 24 }}>
        {isLoading && !config ? (
          <Skeleton active paragraph={{ rows: 4 }} />
        ) : (
          <>
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
