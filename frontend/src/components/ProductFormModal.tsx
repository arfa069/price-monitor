import { useEffect, useState } from 'react'
import { Modal, Form, Input, Select, Switch } from 'antd'
import type { Product } from '@/types'

interface Props {
  open: boolean
  record?: Product
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

export default function ProductFormModal({ open, record, onCancel, onSubmit, confirmLoading }: Props) {
  const [form] = Form.useForm()
  const [autoPlatform, setAutoPlatform] = useState<string | null>(null)

  useEffect(() => {
    if (record) {
      form.setFieldsValue({
        platform: record.platform,
        url: record.url,
        title: record.title,
        active: record.active,
      })
    } else {
      form.resetFields()
    }
    setAutoPlatform(null)
  }, [record, open, form])

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!record) {
      const detected = detectPlatform(e.target.value)
      setAutoPlatform(detected)
      if (detected) form.setFieldValue('platform', detected)
    }
  }

  const handleOk = () => form.validateFields().then((values) => onSubmit(values))

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
      </Form>
    </Modal>
  )
}
