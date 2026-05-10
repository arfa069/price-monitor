import { useState } from 'react'
import { Form, Input, InputNumber, Button, App } from 'antd'
import type { AxiosError } from 'axios'
import { useAuth } from '@/contexts/AuthContext'
import { configApi } from '@/api/config'

export default function SettingsPage() {
  const { user } = useAuth()
  const message = App.useApp().message
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
    <div>
      {/* Page header */}
      <div className="page-header bg-mint">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">偏好设置</p>
            <h1 className="page-title">账号设置</h1>
            <p className="page-subtitle">配置通知渠道与数据保留策略</p>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 560, marginTop: 24 }}>
        <div className="fg-card">
          <div className="fg-card-header">
            <span style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 15, fontWeight: 480, color: '#000' }}>
              个人设置
            </span>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                feishu_webhook_url: user?.feishu_webhook_url || '',
                data_retention_days: user?.data_retention_days || 365,
              }}
              onFinish={handleSubmit}
            >
              <Form.Item
                name="feishu_webhook_url"
                label="飞书 Webhook URL"
                style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
              >
                <Input
                  placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
                  style={{ fontFamily: "'Inter', system-ui, sans-serif", fontSize: 14 }}
                />
              </Form.Item>
              <Form.Item
                name="data_retention_days"
                label="数据保留天数"
                rules={[{ type: 'number', min: 1, max: 3650 }]}
              >
                <InputNumber
                  min={1}
                  max={3650}
                  style={{ width: 200, fontFamily: "'Inter', system-ui, sans-serif" }}
                />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={loading} className="fg-btn-primary">
                  保存
                </Button>
              </Form.Item>
            </Form>
          </div>
        </div>
      </div>
    </div>
  )
}
