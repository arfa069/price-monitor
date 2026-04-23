import { useState } from 'react'
import { Form, InputNumber, Button, Card, message, Alert, Input } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import { isValidCron } from 'cron-validator'
import { useConfig, useUpdateConfig } from '@/hooks/api'

export default function ScheduleConfigPage() {
  const { data: config, isLoading } = useConfig()
  const updateMutation = useUpdateConfig()
  const [form] = Form.useForm()
  const [cronInput, setCronInput] = useState('')
  const [cronValid, setCronValid] = useState<boolean | null>(null)

  const handleCronChange = (value: string) => {
    setCronInput(value)
    if (!value.trim()) { setCronValid(null); return }
    setCronValid(isValidCron(value, { seconds: false }))
  }

  const handleSaveCron = () => {
    if (!cronValid) { message.error('Cron 表达式不合法'); return }
    localStorage.setItem('crawl_cron_draft', cronInput)
    message.success('Cron 草稿已保存（当前仅前端占位，后端调度在阶段2接入）')
  }

  const handleSaveHours = (values: any) => {
    updateMutation.mutate(values, {
      onSuccess: () => message.success('配置已保存'),
      onError: () => message.error('保存失败'),
    })
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <Alert
        message="阶段1占位"
        description="当前仅前端占位，后端调度在阶段2接入"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card title="爬取频率（小时数）" loading={isLoading}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            crawl_frequency_hours: config?.crawl_frequency_hours || 1,
            data_retention_days: config?.data_retention_days || 365,
          }}
          onFinish={handleSaveHours}
        >
          <Form.Item
            name="crawl_frequency_hours"
            label="每隔几小时执行一次"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={168} style={{ width: '100%' }} addonAfter="小时" />
          </Form.Item>
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

      <Card title="Cron 表达式（可选，占位）" style={{ marginTop: 24 }}>
        <Form.Item label="Cron（5段格式）">
          <Input
            value={cronInput}
            onChange={(e) => handleCronChange(e.target.value)}
            placeholder="例如：0 */2 * * *"
          />
        </Form.Item>
        {cronValid === true && (
          <Alert message="Cron 表达式合法" type="success" showIcon style={{ marginBottom: 12 }} />
        )}
        {cronValid === false && (
          <Alert message="Cron 表达式不合法，请使用 5 段格式（分 时 日 月 周）" type="error" showIcon style={{ marginBottom: 12 }} />
        )}
        {cronInput && (
          <Button onClick={handleSaveCron} disabled={!cronValid}>
            保存草稿（localStorage）
          </Button>
        )}
        {!cronInput && (
          <div style={{ color: '#888', fontSize: 12 }}>
            留空即不启用。合法示例：0 9 * * *（每天 9:00）
          </div>
        )}
      </Card>
    </div>
  )
}
