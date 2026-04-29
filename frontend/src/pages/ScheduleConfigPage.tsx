import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Radio,
  Skeleton,
  Space,
  message,
} from 'antd'
import { DeleteOutlined, SaveOutlined, UndoOutlined } from '@ant-design/icons'
import { useConfig, useUpdateConfig } from '@/hooks/api'

const CRON_DRAFT_KEY = 'crawl_cron_draft'
const TZ_DRAFT_KEY = 'crawl_timezone_draft'

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
  crawl_cron?: string
  crawl_timezone?: string
}

export default function ScheduleConfigPage() {
  const { data: config, isLoading, isError, refetch } = useConfig()
  const updateMutation = useUpdateConfig()
  const [form] = Form.useForm<ScheduleFormValues>()
  const [draftDismissed, setDraftDismissed] = useState(false)

  useEffect(() => {
    if (!config) return
    form.setFieldsValue({
      schedule_mode: config.crawl_cron ? 'cron' : 'hours',
      crawl_frequency_hours: config.crawl_frequency_hours || 1,
      data_retention_days: config.data_retention_days || 365,
      crawl_cron: config.crawl_cron || '',
      crawl_timezone: config.crawl_timezone || 'Asia/Shanghai',
    })
  }, [config, form])

  const scheduleMode =
    Form.useWatch('schedule_mode', form) ?? (config?.crawl_cron ? 'cron' : 'hours')
  const cronInput = Form.useWatch('crawl_cron', form) ?? ''
  const cronTimezone = Form.useWatch('crawl_timezone', form) ?? 'Asia/Shanghai'
  const cronValid = useMemo(
    () => (cronInput.trim() ? isValidCronFormat(cronInput) : null),
    [cronInput],
  )

  const pendingDraft = useMemo(() => {
    if (!config || draftDismissed) return null
    const backendCron = config.crawl_cron || ''
    const draftCron = localStorage.getItem(CRON_DRAFT_KEY) || ''
    const draftTz =
      localStorage.getItem(TZ_DRAFT_KEY) || config.crawl_timezone || 'Asia/Shanghai'

    if (!draftCron || draftCron === backendCron) return null
    return { cron: draftCron, tz: draftTz }
  }, [config, draftDismissed])

  const handleRestoreDraft = () => {
    if (!pendingDraft) return
    form.setFieldsValue({
      schedule_mode: 'cron',
      crawl_cron: pendingDraft.cron,
      crawl_timezone: pendingDraft.tz,
    })
    setDraftDismissed(true)
  }

  const handleDiscardDraft = () => {
    localStorage.removeItem(CRON_DRAFT_KEY)
    localStorage.removeItem(TZ_DRAFT_KEY)
    setDraftDismissed(true)
    if (!config) return
    form.setFieldsValue({
      schedule_mode: config.crawl_cron ? 'cron' : 'hours',
      crawl_cron: config.crawl_cron || '',
      crawl_timezone: config.crawl_timezone || 'Asia/Shanghai',
    })
  }

  const handleCronChange = (value: string) => {
    form.setFieldValue('crawl_cron', value)
  }

  const handleSaveCron = async () => {
    if (cronValid !== true) {
      message.error('Cron 表达式不合法')
      return
    }
    try {
      await updateMutation.mutateAsync({
        crawl_cron: cronInput.trim(),
        crawl_timezone: cronTimezone,
      })
      localStorage.removeItem(CRON_DRAFT_KEY)
      localStorage.removeItem(TZ_DRAFT_KEY)
      message.success('Cron 配置已保存')
      refetch()
    } catch {
      message.error('保存失败')
    }
  }

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

  const handleSaveDraft = () => {
    localStorage.setItem(CRON_DRAFT_KEY, cronInput)
    localStorage.setItem(TZ_DRAFT_KEY, cronTimezone)
    message.success('草稿已保存到本地')
  }

  return (
    <div>
      {pendingDraft && (
        <Alert
          message="检测到未保存的草稿"
          description={`本地草稿: ${pendingDraft.cron}`}
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
          action={
            <Space orientation="vertical">
              <Button size="small" icon={<UndoOutlined />} onClick={handleRestoreDraft}>
                恢复草稿
              </Button>
              <Button size="small" danger icon={<DeleteOutlined />} onClick={handleDiscardDraft}>
                丢弃草稿
              </Button>
            </Space>
          }
        />
      )}

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
              <div style={{ maxWidth: 520 }}>
                <Form.Item label="Cron 表达式（5 段）">
                  <Input
                    value={cronInput}
                    onChange={(e) => handleCronChange(e.target.value)}
                    placeholder="例如：0 9 * * *"
                  />
                </Form.Item>
                <Form.Item name="crawl_timezone" label="时区">
                  <Input placeholder="例如：Asia/Shanghai" />
                </Form.Item>
                {cronValid === true && (
                  <Alert
                    message="Cron 表达式合法"
                    type="success"
                    showIcon
                    style={{ marginBottom: 12 }}
                  />
                )}
                {cronValid === false && (
                  <Alert
                    message="Cron 表达式不合法，请使用 5 段格式（分 时 日 月 周）"
                    type="error"
                    showIcon
                    style={{ marginBottom: 12 }}
                  />
                )}
                <Space style={{ display: 'flex', width: '100%' }}>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    onClick={handleSaveCron}
                    disabled={cronValid !== true}
                    loading={updateMutation.isPending}
                  >
                    保存 Cron 配置
                  </Button>
                  <Button onClick={handleSaveDraft} disabled={cronValid !== true}>
                    保存草稿（本地）
                  </Button>
                </Space>
              </div>
            )}
          </Card>
        )}
      </Form>

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
