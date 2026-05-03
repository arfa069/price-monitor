import { useEffect } from 'react'
import { AlertOutlined } from '@ant-design/icons'
import { Divider, Form, Input, InputNumber, Modal, Select, Space, Switch } from 'antd'
import type { Product, ProductFormValues } from '@/types'

type AlertFormValues = {
  existingId: number | null
  enabled: boolean
  threshold: number
}

export type ProductFormSubmitValues = ProductFormValues & {
  alert: AlertFormValues
}

interface Props {
  open: boolean
  record?: Product
  existingAlert?: { id: number; active: boolean; threshold_percent: number } | null
  onCancel: () => void
  onSubmit: (values: ProductFormSubmitValues) => void
  confirmLoading?: boolean
}

type ProductFormFields = ProductFormValues & {
  alert_enabled?: boolean
  alert_threshold?: number
}

const detectPlatform = (url: string): ProductFormValues['platform'] | null => {
  const lowerUrl = url.toLowerCase()
  if (lowerUrl.includes('jd.com') || lowerUrl.includes('item.jd')) return 'jd'
  if (lowerUrl.includes('taobao.com') || lowerUrl.includes('tmall.com')) return 'taobao'
  if (lowerUrl.includes('amazon.')) return 'amazon'
  return null
}

export default function ProductFormModal({
  open,
  record,
  existingAlert,
  onCancel,
  onSubmit,
  confirmLoading,
}: Props) {
  const [form] = Form.useForm<ProductFormFields>()

  useEffect(() => {
    if (!open) return
    if (record) {
      form.setFieldsValue({
        platform: record.platform as ProductFormValues['platform'],
        url: record.url,
        title: record.title || undefined,
        active: record.active,
        alert_enabled: existingAlert?.active ?? false,
        alert_threshold: existingAlert?.threshold_percent ?? 5,
      })
      return
    }
    form.resetFields()
    form.setFieldsValue({
      active: true,
      alert_enabled: false,
      alert_threshold: 5,
    })
  }, [open, record, existingAlert, form])

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (record) return
    const detected = detectPlatform(e.target.value)
    if (detected) form.setFieldValue('platform', detected)
  }

  const handleOk = () =>
    form.validateFields().then((values) => {
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
        <Form.Item name="platform" label="平台" rules={[{ required: true, message: '请选择平台' }]}>
          <Select
            options={[
              { label: '淘宝', value: 'taobao' },
              { label: '京东', value: 'jd' },
              { label: '亚马逊', value: 'amazon' },
            ]}
          />
        </Form.Item>
        <Form.Item
          name="url"
          label="商品链接"
          rules={[
            { required: true, message: '请输入商品链接' },
            { type: 'url', message: 'URL 格式不正确' },
          ]}
        >
          <Input placeholder="https://..." onChange={handleUrlChange} autoComplete="off" />
        </Form.Item>
        <Form.Item name="title" label="标题">
          <Input placeholder="留空时自动抓取" autoComplete="off" />
        </Form.Item>
        <Form.Item name="active" label="启用" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Divider orientation="horizontal" plain>
          <Space>
            <AlertOutlined />
            价格告警设置
          </Space>
        </Divider>

        <Form.Item name="alert_enabled" label="启用告警" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.alert_enabled !== curr.alert_enabled}>
          {({ getFieldValue }) =>
            getFieldValue('alert_enabled') ? (
              <Form.Item
                name="alert_threshold"
                label="降价阈值"
                rules={[{ required: true, message: '请输入阈值' }]}
              >
                <Space.Compact>
                  <InputNumber min={1} max={100} style={{ width: 80 }} />
                  <Input value="%" disabled style={{ width: 40 }} />
                </Space.Compact>
              </Form.Item>
            ) : null
          }
        </Form.Item>
      </Form>
    </Modal>
  )
}
