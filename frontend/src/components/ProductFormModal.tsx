import { useEffect } from 'react'
import { Modal, Form, Input, Select, Switch, InputNumber, Divider, Space } from 'antd'
import { AlertOutlined } from '@ant-design/icons'
import type { Product } from '@/types'

interface Props {
  open: boolean
  record?: Product
  existingAlert?: { id: number; active: boolean; threshold_percent: number } | null
  onCancel: () => void
  onSubmit: (values: any) => void
  confirmLoading?: boolean
}

const detectPlatform = (url: string): string | null => {
  const u = url.toLowerCase()
  if (u.includes('jd.com') || u.includes('item.jd')) return 'jd'
  if (u.includes('taobao.com') || u.includes('tmall.com')) return 'taobao'
  if (u.includes('amazon.')) return 'amazon'
  return null
}

export default function ProductFormModal({ open, record, existingAlert, onCancel, onSubmit, confirmLoading }: Props) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (record) {
      form.setFieldsValue({
        platform: record.platform,
        url: record.url,
        title: record.title,
        active: record.active,
        alert_enabled: existingAlert?.active ?? false,
        alert_threshold: existingAlert?.threshold_percent ?? 5,
      })
    } else {
      form.resetFields(['alert_enabled', 'alert_threshold'])
    }
  }, [record, open, form, existingAlert])

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!record) {
      const detected = detectPlatform(e.target.value)
      if (detected) form.setFieldValue('platform', detected)
    }
  }

  const handleOk = () => form.validateFields().then((values) => {
    // Extract alert settings from form values
    const { alert_enabled, alert_threshold, ...productValues } = values
    onSubmit({
      ...productValues,
      alert: {
        existingId: existingAlert?.id ?? null,
        enabled: alert_enabled ?? false,
        threshold: alert_threshold ?? 5,
      },
    })
  })

  return (
    <Modal
      title={record ? '编辑商品' : '新增商品'}
      open={open}
      onCancel={onCancel}
      onOk={handleOk}
      confirmLoading={confirmLoading}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 20 }}>
        <Form.Item
          name="platform"
          label="平台"
          rules={[{ required: true, message: '请选择平台' }]}
        >
          <Select options={[
            { label: '淘宝', value: 'taobao' },
            { label: '京东', value: 'jd' },
            { label: '亚马逊', value: 'amazon' },
          ]} />
        </Form.Item>
        <Form.Item
          name="url"
          label="商品链接"
          rules={[
            { required: true, message: '请输入商品链接' },
            { type: 'url', message: 'URL 格式不正确' },
          ]}
        >
          <Input placeholder="https://..." onChange={handleUrlChange} />
        </Form.Item>
        <Form.Item name="title" label="标题">
          <Input placeholder="留空将自动抓取" />
        </Form.Item>
        <Form.Item name="active" label="启用" valuePropName="checked" initialValue>
          <Switch />
        </Form.Item>

        <Divider orientation="horizontal" plain>
          <Space>
            <AlertOutlined />
            价格告警设置
          </Space>
        </Divider>

        <Form.Item name="alert_enabled" label="启用告警" valuePropName="checked" initialValue={false}>
          <Switch />
        </Form.Item>

        <Form.Item
          noStyle
          shouldUpdate={(prev, curr) => prev.alert_enabled !== curr.alert_enabled}
        >
          {({ getFieldValue }) =>
            getFieldValue('alert_enabled') ? (
              <Form.Item
                name="alert_threshold"
                label="降价阈值"
                rules={[{ required: true, message: '请输入阈值' }]}
              >
                <InputNumber
                  min={1}
                  max={100}
                  addonAfter="%"
                  style={{ width: 120 }}
                />
              </Form.Item>
            ) : null
          }
        </Form.Item>
      </Form>
    </Modal>
  )
}
