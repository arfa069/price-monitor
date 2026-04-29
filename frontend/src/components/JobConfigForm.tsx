import { useEffect, useRef } from 'react'
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
  const recordRef = useRef(record)
  recordRef.current = record

  useEffect(() => {
    if (!open) return
    if (recordRef.current) {
      setTimeout(() => {
        form.setFieldsValue(recordRef.current!)
        // 自动从 URL 解析 keyword（编辑已有配置时补充显示）
        try {
          const parsed = new URL(recordRef.current.url)
          const query = parsed.searchParams.get('query')
          if (query) form.setFieldsValue({ keyword: query })
        } catch {
          // ignore
        }
      }, 0)
      return
    }
    form.resetFields()
    form.setFieldsValue({
      active: true,
      notify_on_new: true,
    })
  }, [open, form])

  const handleCancel = () => {
    form.resetFields()
    onCancel()
  }

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (recordRef.current) return
    const url = e.target.value
    try {
      const parsed = new URL(url)
      const query = parsed.searchParams.get('query')
      if (query) form.setFieldsValue({ keyword: query })
    } catch {
      // invalid URL, ignore
    }
  }

  const handleOk = async () => {
    const values = await form.validateFields()
    await onSubmit(values)
    form.resetFields()
  }

  return (
    <Modal
      title={record ? '编辑职位配置' : '新增职位配置'}
      open={open}
      onCancel={handleCancel}
      onOk={handleOk}
      confirmLoading={confirmLoading}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label="配置名称"
          rules={[{ required: true, message: '请输入配置名称' }]}
        >
          <Input placeholder="例如：上海前端岗位" autoComplete="off" name="name" />
        </Form.Item>
        <Form.Item
          name="url"
          label="Boss 搜索 URL"
          rules={[{ required: true, message: '请输入 URL' }, { type: 'url', message: 'URL 格式不正确' }]}
        >
<Input placeholder="https://www.zhipin.com/web/geek/job?query=…" autoComplete="off" name="url" onChange={handleUrlChange} />
        </Form.Item>
        <Form.Item name="keyword" label="关键词">
          <Input placeholder="例如：React" autoComplete="off" name="keyword" />
        </Form.Item>
        <Form.Item name="city_code" label="城市代码">
          <Input placeholder="例如：101020100" autoComplete="off" name="city_code" />
        </Form.Item>
        <Form.Item name="salary_min" label="最低薪资(K)">
          <InputNumber min={0} style={{ width: '100%' }} autoComplete="off" name="salary_min" />
        </Form.Item>
        <Form.Item name="salary_max" label="最高薪资(K)">
          <InputNumber min={0} style={{ width: '100%' }} autoComplete="off" name="salary_max" />
        </Form.Item>
        <Form.Item name="experience" label="经验要求">
          <Input placeholder="例如：3-5年" autoComplete="off" name="experience" />
        </Form.Item>
        <Form.Item name="education" label="学历要求">
          <Input placeholder="例如：本科" autoComplete="off" name="education" />
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
