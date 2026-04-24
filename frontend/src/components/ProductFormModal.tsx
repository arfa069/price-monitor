import { useState, useEffect } from 'react'
import { Modal, Form, Input, Select, Switch, InputNumber, Button, Divider, Space, Popconfirm } from 'antd'
import { AlertOutlined, DeleteOutlined } from '@ant-design/icons'
import { useAlerts, useCreateAlert, useUpdateAlert, useDeleteAlert } from '@/hooks/api'
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

  const [alertEnabled, setAlertEnabled] = useState(false)
  const [alertThreshold, setAlertThreshold] = useState(5)
  const [currentAlertId, setCurrentAlertId] = useState<number | null>(null)

  const { data: alertData, refetch: refetchAlert } = useAlerts(record?.id)
  const createAlertMutation = useCreateAlert()
  const updateAlertMutation = useUpdateAlert()
  const deleteAlertMutation = useDeleteAlert()

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
  }, [record, open, form])

  useEffect(() => {
    if (alertData && alertData.length > 0) {
      const alert = alertData[0]
      setCurrentAlertId(alert.id)
      setAlertEnabled(alert.active)
      setAlertThreshold(Number(alert.threshold_percent) || 5)
    } else {
      setCurrentAlertId(null)
      setAlertEnabled(false)
      setAlertThreshold(5)
    }
  }, [alertData])

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!record) {
      const detected = detectPlatform(e.target.value)
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

      <Divider orientation="left" plain>
        <Space>
          <AlertOutlined />
          价格告警设置
        </Space>
      </Divider>

      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <span>启用告警：</span>
          <Switch
            checked={alertEnabled}
            onChange={async (checked) => {
              setAlertEnabled(checked)
              if (currentAlertId) {
                await updateAlertMutation.mutateAsync({
                  id: currentAlertId,
                  data: { active: checked },
                })
                refetchAlert()
              } else if (checked && record?.id) {
                const res = await createAlertMutation.mutateAsync({
                  product_id: record.id,
                  threshold_percent: alertThreshold,
                  active: true,
                })
                setCurrentAlertId(res.id)
                refetchAlert()
              }
            }}
          />
        </Space>

        <Space>
          <span>降价阈值：</span>
          <InputNumber
            min={1}
            max={100}
            value={alertThreshold}
            onChange={(val) => setAlertThreshold(val || 5)}
            disabled={!currentAlertId}
            addonAfter="%"
            style={{ width: 120 }}
          />
          <Button
            size="small"
            onClick={async () => {
              if (currentAlertId) {
                await updateAlertMutation.mutateAsync({
                  id: currentAlertId,
                  data: { threshold_percent: alertThreshold },
                })
                refetchAlert()
              }
            }}
          >
            保存阈值
          </Button>
        </Space>

        {currentAlertId && (
          <Popconfirm
            title="确定删除此商品的告警？"
            onConfirm={async () => {
              await deleteAlertMutation.mutateAsync(currentAlertId)
              setCurrentAlertId(null)
              setAlertEnabled(false)
              refetchAlert()
            }}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除告警
            </Button>
          </Popconfirm>
        )}
      </Space>
    </Modal>
  )
}
