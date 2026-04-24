import { useState, useEffect } from 'react'
import { Form, InputNumber, Button, Card, message, Alert, Input, Radio, Space, Skeleton } from 'antd'
import { SaveOutlined, UndoOutlined, DeleteOutlined } from '@ant-design/icons'
import { useConfig, useUpdateConfig } from '@/hooks/api'

const CRON_DRAFT_KEY = 'crawl_cron_draft'
const TZ_DRAFT_KEY = 'crawl_timezone_draft'

type ScheduleMode = 'hours' | 'cron'

// Cron validation (mirrors backend regex in app/schemas/user.py)
const CRON_SEGMENT_RE = /^\*|[0-9]+(?:-[0-9]+)?(?:\/[0-9]+)?$/

const isValidCronFormat = (value: string): boolean => {
  const parts = value.trim().split(/\s+/)
  if (parts.length !== 5) return false
  return parts.every(p => CRON_SEGMENT_RE.test(p))
}

export default function ScheduleConfigPage() {
  const { data: config, isLoading, isError, refetch } = useConfig()
  const updateMutation = useUpdateConfig()
  const [form] = Form.useForm()
  const [scheduleMode, setScheduleMode] = useState<ScheduleMode>('hours')
  const [cronInput, setCronInput] = useState('')
  const [cronValid, setCronValid] = useState<boolean | null>(null)
  const [cronTimezone, setCronTimezone] = useState('Asia/Shanghai')
  const [draftDetected, setDraftDetected] = useState(false)
  const [pendingDraft, setPendingDraft] = useState<{ cron: string; tz: string } | null>(null)

  // Sync form with config data when it arrives
  useEffect(() => {
    if (!config) return

    // Detect draft vs backend difference
    const backendCron = config.crawl_cron || ''
    const draftCron = localStorage.getItem(CRON_DRAFT_KEY) || ''
    const draftTz = localStorage.getItem(TZ_DRAFT_KEY) || config.crawl_timezone || 'Asia/Shanghai'

    if (draftCron && draftCron !== backendCron) {
      setPendingDraft({ cron: draftCron, tz: draftTz })
      setDraftDetected(true)
    } else {
      // No draft or draft matches backend — initialize from backend
      setCronInput(backendCron)
      setCronValid(backendCron ? isValidCronFormat(backendCron) : null)
      setDraftDetected(false)
      setPendingDraft(null)
      // Determine mode
      setScheduleMode(backendCron ? 'cron' : 'hours')
    }
  }, [config])

  // Draft restoration
  const handleRestoreDraft = () => {
    if (pendingDraft) {
      setCronInput(pendingDraft.cron)
      setCronValid(isValidCronFormat(pendingDraft.cron))
      setCronTimezone(pendingDraft.tz)
      setScheduleMode('cron')
      setDraftDetected(false)
      setPendingDraft(null)
    }
  }

  const handleDiscardDraft = () => {
    localStorage.removeItem(CRON_DRAFT_KEY)
    localStorage.removeItem(TZ_DRAFT_KEY)
    setPendingDraft(null)
    setDraftDetected(false)
    setCronInput(config?.crawl_cron || '')
    setCronValid(config?.crawl_cron ? isValidCronFormat(config.crawl_cron) : null)
    setCronTimezone(config?.crawl_timezone || 'Asia/Shanghai')
    setScheduleMode(config?.crawl_cron ? 'cron' : 'hours')
  }

  const handleCronChange = (value: string) => {
    setCronInput(value)
    if (!value.trim()) { setCronValid(null); return }
    setCronValid(isValidCronFormat(value))
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

  const handleSaveHours = async (values: { crawl_frequency_hours?: number; data_retention_days?: number }) => {
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
      {/* Draft restoration alert */}
      {draftDetected && pendingDraft && (
        <Alert
          message="检测到未保存的草稿"
          description={`本地草稿: ${pendingDraft.cron}`}
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
          action={
            <Space direction="vertical">
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

      {/* API error state */}
      {isError && !isLoading && (
        <Alert
          type="error"
          message="加载失败"
          description="无法获取配置信息，请检查网络或重试。"
          action={<Button size="small" onClick={() => refetch()}>重试</Button>}
          style={{ marginBottom: 24 }}
        />
      )}

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          crawl_frequency_hours: config?.crawl_frequency_hours || 1,
        }}
        onFinish={handleSaveHours}
      >
        {isLoading && !config ? (
          <Card title="爬取频率配置">
            <Skeleton active paragraph={{ rows: 4 }} />
          </Card>
        ) : (
<Card title="爬取频率配置">
          {/* Schedule mode selector */}
          <Form.Item label="调度模式" style={{ marginBottom: 16 }}>
            <Radio.Group
              value={scheduleMode}
              onChange={e => setScheduleMode(e.target.value)}
            >
              <Radio.Button value="hours">间隔模式</Radio.Button>
              <Radio.Button value="cron">Cron 模式</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {/* Hours-based config */}
          {scheduleMode === 'hours' && (
            <>
              <Form.Item
                name="crawl_frequency_hours"
                label="每隔几小时执行一次"
                rules={[{ required: scheduleMode === 'hours' }]}
              >
                <InputNumber min={1} max={168} style={{ width: '100%' }} addonAfter="小时" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" icon={<SaveOutlined />} htmlType="submit" loading={updateMutation.isPending}>
                  保存配置
                </Button>
              </Form.Item>
            </>
          )}

          {/* Cron-based config */}
          {scheduleMode === 'cron' && (
            <div style={{ maxWidth: 520 }}>
              <Form.Item label="Cron 表达式（5段格式）">
                <Input
                  value={cronInput}
                  onChange={e => handleCronChange(e.target.value)}
                  placeholder="例如：0 9 * * *"
                />
              </Form.Item>
              {cronValid === true && (
                <Alert message="Cron 表达式合法" type="success" showIcon style={{ marginBottom: 12 }} />
              )}
              {cronValid === false && (
                <Alert message="Cron 表达式不合法，请使用 5 段格式（分 时 日 月 周）" type="error" showIcon style={{ marginBottom: 12 }} />
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
              {!cronInput && (
                <div style={{ color: '#64748b', fontSize: 12, marginTop: 8 }}>
                  留空即不启用。合法示例：0 9 * * *（每天 9:00）
                </div>
              )}
            </div>
          )}
        </Card>
        )}
      </Form>

      {/* Webhook config */}
      {isLoading && !config ? (
        <Card title="数据保留（其他配置）" style={{ marginTop: 24 }}>
          <Skeleton active paragraph={{ rows: 2 }} />
        </Card>
      ) : (
      <Card title="数据保留（其他配置）" style={{ marginTop: 24 }}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            data_retention_days: config?.data_retention_days || 365,
          }}
          onFinish={handleSaveHours}
        >
          <Form.Item
            name="data_retention_days"
            label="数据保留天数"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={3650} style={{ width: '100%' }} addonAfter="天" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<SaveOutlined />} htmlType="submit" loading={updateMutation.isPending}>
              保存配置
            </Button>
          </Form.Item>
        </Form>
      </Card>
      )}
    </div>
  )
}
