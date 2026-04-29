import { useEffect } from 'react'
import { Form, Input, InputNumber, Modal, Switch } from 'antd'
import type {
  JobSearchConfig,
  JobSearchConfigCreate,
} from '@/types'

interface JobConfigFormProps {
  open: boolean
  record?: JobSearchConfig | null
  onCancel: () => void
  onSubmit: (values: Partial<JobSearchConfigCreate>) => Promise<void>
  confirmLoading?: boolean
}

export default function JobConfigForm({
  open,
  record,
  onCancel,
  onSubmit,
  confirmLoading,
}: JobConfigFormProps) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (!open) return
    if (record) {
      form.setFieldsValue(record)
      return
    }
    form.resetFields()
    form.setFieldsValue({
      active: true,
      notify_on_new: true,
    })
  }, [open, record, form])

  const handleOk = async () => {
    const values = await form.validateFields()
    await onSubmit(values)
    form.resetFields()
  }

  return (
    <Modal
      title={record ? '编辑职位配置' : '新增职位配置'}
      open={open}
      onCancel={onCancel}
      onOk={handleOk}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Form.Item
          name="name"
          label="配置名称"
          rules={[{ required: true, message: '请输入配置名称' }]}
        >
          <Input placeholder="例如：上海前端岗位" autocomplete="off" name="name" />
        </Form.Item>
        <Form.Item
          name="url"
          label="Boss 搜索 URL"
          rules={[{ required: true, message: '请输入 URL' }, { type: 'url', message: 'URL 格式不正确' }]}
        >
          <Input placeholder="https://www.zhipin.com/web/geek/job?query=..." autocomplete="off" name="url" />
        </Form.Item>
        <Form.Item name="keyword" label="关键词">
          <Input placeholder="例如：React" autocomplete="off" name="keyword" />
        </Form.Item>
        <Form.Item name="city_code" label="城市代码">
          <Input placeholder="例如：101020100" autocomplete="off" name="city_code" />
        </Form.Item>
        <Form.Item name="salary_min" label="最低薪资(K)">
          <InputNumber min={0} style={{ width: '100%' }} autocomplete="off" name="salary_min" />
        </Form.Item>
        <Form.Item name="salary_max" label="最高薪资(K)">
          <InputNumber min={0} style={{ width: '100%' }} autocomplete="off" name="salary_max" />
        </Form.Item>
        <Form.Item name="experience" label="经验要求">
          <Input placeholder="例如：3-5年" autocomplete="off" name="experience" />
        </Form.Item>
        <Form.Item name="education" label="学历要求">
          <Input placeholder="例如：本科" autocomplete="off" name="education" />
        </Form.Item>
        <Form.Item name="active" label="启用配置" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="notify_on_new" label="新岗位通知" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  )
}
