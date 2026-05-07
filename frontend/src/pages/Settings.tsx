import { useState } from 'react'
import { Card, Form, Input, InputNumber, Button, message } from 'antd'
import type { AxiosError } from 'axios'
import { useAuth } from '@/contexts/AuthContext'
import { configApi } from '@/api/config'

export default function SettingsPage() {
  const { user } = useAuth()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: { feishu_webhook_url?: string; data_retention_days?: number }) => {
    setLoading(true)
    try {
      await configApi.update(values)
      message.success('设置已保存')
      window.location.reload()
    } catch (error: unknown) {
      const axiosError = error as AxiosError<{ detail?: string }>
      message.error(axiosError.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <Card title="个人设置">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            feishu_webhook_url: user?.feishu_webhook_url || '',
            data_retention_days: user?.data_retention_days || 365,
          }}
          onFinish={handleSubmit}
        >
          <Form.Item name="feishu_webhook_url" label="飞书 Webhook URL">
            <Input placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx" />
          </Form.Item>
          <Form.Item name="data_retention_days" label="数据保留天数" rules={[{ type: 'number', min: 1, max: 3650 }]}>
            <InputNumber min={1} max={3650} style={{ width: 200 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
