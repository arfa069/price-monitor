import { useEffect } from 'react'
import { Form, Input, InputNumber, Modal, Switch } from 'antd'
import type { JobSearchConfig, JobSearchConfigCreate } from '@/types'

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
      enable_match_analysis: false,
      deactivation_threshold: 3,
    })
  }, [open, record, form])

  const handleCancel = () => {
    form.resetFields()
    onCancel()
  }

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (record) return
    const url = e.target.value
    try {
      const parsed = new URL(url)
      const query = parsed.searchParams.get('query')
      if (query) form.setFieldsValue({ keyword: query })
    } catch {
      // ignore malformed URL while typing
    }
  }

  const handleOk = async () => {
    const values = await form.validateFields()
    await onSubmit(values)
    form.resetFields()
  }

  return (
    <Modal
      title={record ? 'Edit Job Config' : 'Add Job Config'}
      open={open}
      onCancel={handleCancel}
      onOk={handleOk}
      confirmLoading={confirmLoading}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="name" label="Config Name" rules={[{ required: true, message: 'Please enter config name' }]}>
          <Input placeholder="e.g. Shanghai Frontend Jobs" autoComplete="off" />
        </Form.Item>
        <Form.Item
          name="url"
          label="Boss Search URL"
          rules={[
            { required: true, message: 'Please enter URL' },
            { type: 'url', message: 'Invalid URL format' },
          ]}
        >
          <Input
            placeholder="https://www.zhipin.com/web/geek/job?query=frontend"
            autoComplete="off"
            onChange={handleUrlChange}
          />
        </Form.Item>
        <Form.Item name="keyword" label="Keyword">
          <Input placeholder="e.g. React" autoComplete="off" />
        </Form.Item>
        <Form.Item name="city_code" label="City Code">
          <Input placeholder="e.g. 101020100" autoComplete="off" />
        </Form.Item>
        <Form.Item name="salary_min" label="Min Salary (K)">
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="salary_max" label="Max Salary (K)">
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="experience" label="Experience">
          <Input placeholder="e.g. 3-5 years" autoComplete="off" />
        </Form.Item>
        <Form.Item name="education" label="Education">
          <Input placeholder="e.g. Bachelor" autoComplete="off" />
        </Form.Item>
        <Form.Item name="deactivation_threshold" label="Deactivation Threshold">
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="active" label="Enable Config" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="notify_on_new" label="New Job Notification" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="enable_match_analysis" label="Auto Match After Crawl" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  )
}
