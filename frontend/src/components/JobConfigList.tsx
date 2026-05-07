import { useState } from 'react'
import {
  Button,
  Card,
  Empty,
  Popconfirm,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
  useApp,
} from 'antd'
import {
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import JobConfigForm from '@/components/JobConfigForm'
import type { JobSearchConfig, JobSearchConfigCreate } from '@/types'

interface JobConfigListProps {
  configs?: JobSearchConfig[]
  isLoading?: boolean
  onCreate: (data: JobSearchConfigCreate) => Promise<void>
  onUpdate: (id: number, data: Partial<JobSearchConfigCreate>) => Promise<void>
  onDelete: (id: number) => Promise<void>
  onCrawl: (id: number) => Promise<void>
  createLoading?: boolean
  updateLoading?: boolean
  crawlLoading?: boolean
}

export default function JobConfigList({
  configs,
  isLoading,
  onCreate,
  onUpdate,
  onDelete,
  onCrawl,
  createLoading,
  updateLoading,
  crawlLoading,
}: JobConfigListProps) {
  const [createOpen, setCreateOpen] = useState(false)
  const [editRecord, setEditRecord] = useState<JobSearchConfig | null>(null)
  const { message } = useApp()

  const handleCreate = async (data: Partial<JobSearchConfigCreate>) => {
    if (!data.name || !data.url) throw new Error('missing required fields')
    await onCreate(data as JobSearchConfigCreate)
    setCreateOpen(false)
    message.success('配置创建成功')
  }

  const handleUpdate = async (data: Partial<JobSearchConfigCreate>) => {
    if (!editRecord) return
    await onUpdate(editRecord.id, data)
    setEditRecord(null)
    message.success('配置更新成功')
  }

  const handleToggleMatch = async (config: JobSearchConfig, checked: boolean) => {
    await onUpdate(config.id, { enable_match_analysis: checked })
    message.success(checked ? '已开启自动匹配' : '已关闭自动匹配')
  }

  return (
    <div>
      <Space style={{ marginBottom: 12, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          职位搜索配置
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新增配置
        </Button>
      </Space>

      {isLoading ? (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Spin />
        </div>
      ) : !configs?.length ? (
        <Empty description="暂无配置" />
      ) : (
        <Space orientation="vertical" style={{ width: '100%' }}>
          {configs.map((config) => (
            <Card
              key={config.id}
              size="small"
              title={config.name}
              extra={
                <Space>
                  <Tag color={config.active ? 'success' : 'default'}>
                    {config.active ? '启用' : '停用'}
                  </Tag>
                  <Tag color={config.notify_on_new ? 'processing' : 'default'}>
                    {config.notify_on_new ? '新职位通知' : '通知关闭'}
                  </Tag>
                  <Switch
                    size="small"
                    checked={config.enable_match_analysis}
                    checkedChildren="自动匹配"
                    unCheckedChildren="自动匹配"
                    onChange={(checked) => void handleToggleMatch(config, checked)}
                  />
                </Space>
              }
            >
              <Typography.Paragraph ellipsis={{ rows: 1 }} style={{ marginBottom: 8 }}>
                {config.url}
              </Typography.Paragraph>
              <Space wrap size={8}>
                <Button
                  icon={<PlayCircleOutlined />}
                  loading={crawlLoading}
                  onClick={() => onCrawl(config.id)}
                >
                  抓取
                </Button>
                <Button icon={<EditOutlined />} onClick={() => setEditRecord(config)}>
                  编辑
                </Button>
                <Popconfirm title="确认删除这条配置吗？" onConfirm={() => onDelete(config.id)}>
                  <Button danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </Card>
          ))}
        </Space>
      )}

      <JobConfigForm
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onSubmit={handleCreate}
        confirmLoading={createLoading}
      />
      <JobConfigForm
        open={!!editRecord}
        record={editRecord}
        onCancel={() => setEditRecord(null)}
        onSubmit={handleUpdate}
        confirmLoading={updateLoading}
      />
    </div>
  )
}
