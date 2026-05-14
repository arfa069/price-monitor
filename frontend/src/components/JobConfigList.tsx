import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  App,
  Button,
  Card,
  Empty,
  Popconfirm,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
} from 'antd'
import {
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import JobConfigForm from '@/components/JobConfigForm'
import { useStaggerAnimation } from '@/hooks/useStaggerAnimation'
import type { JobSearchConfig, JobSearchConfigCreate } from '@/types'

interface JobConfigListProps {
  configs?: JobSearchConfig[]
  isLoading?: boolean
  onCreate: (data: JobSearchConfigCreate) => Promise<void>
  onUpdate: (id: number, data: Partial<JobSearchConfigCreate>) => Promise<void>
  onDelete: (id: number) => Promise<void>
  onCrawl?: (id: number) => Promise<void>
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
  const message = App.useApp().message
  const stagger = useStaggerAnimation(0.05, 0.05)
  const [createOpen, setCreateOpen] = useState(false)
  const [editRecord, setEditRecord] = useState<JobSearchConfig | null>(null)

  const handleCreate = async (data: Partial<JobSearchConfigCreate>) => {
    if (!data.name || !data.url) throw new Error('missing required fields')
    await onCreate(data as JobSearchConfigCreate)
    setCreateOpen(false)
    message.success('Config created successfully')
  }

  const handleUpdate = async (data: Partial<JobSearchConfigCreate>) => {
    if (!editRecord) return
    await onUpdate(editRecord.id, data)
    setEditRecord(null)
    message.success('Config updated successfully')
  }

  const handleToggleMatch = async (config: JobSearchConfig, checked: boolean) => {
    await onUpdate(config.id, { enable_match_analysis: checked })
    message.success(checked ? 'Auto-match enabled' : 'Auto-match disabled')
  }

  return (
    <div>
      <Space style={{ marginBottom: 12, width: '100%', justifyContent: 'space-between' }}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          Job Search Config
        </Typography.Title>
        <Button
          icon={<PlusOutlined />}
          onClick={() => setCreateOpen(true)}
          className="fg-btn-secondary"
        >
          Add Config
        </Button>
      </Space>

      {isLoading ? (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Spin />
        </div>
      ) : !configs?.length ? (
        <Empty description="No Configs" />
      ) : (
        <motion.div
          variants={stagger.container}
          initial="hidden"
          animate="show"
          style={{ width: '100%' }}
        >
        <Space orientation="vertical" style={{ width: '100%' }}>
          {configs.map((config) => (
            <motion.div key={config.id} variants={stagger.item}>
              <Card
                size="small"
                title={config.name}
                extra={
                  <Space>
                    <Tag color={config.active ? 'success' : 'default'}>
                      {config.active ? 'Enabled' : 'Disabled'}
                    </Tag>
                    <Tag color={config.notify_on_new ? 'processing' : 'default'}>
                      {config.notify_on_new ? 'New Job Notification' : 'Notification Off'}
                    </Tag>
                    <Switch
                      size="small"
                      checked={config.enable_match_analysis}
                      checkedChildren="Auto-match"
                      unCheckedChildren="Auto-match"
                      onChange={(checked) => void handleToggleMatch(config, checked)}
                    />
                  </Space>
                }
              >
                <Typography.Paragraph ellipsis={{ rows: 1 }} style={{ marginBottom: 8 }}>
                  {config.url}
                </Typography.Paragraph>
                <Space wrap size={8}>
                  {onCrawl && (
                    <Button
                      icon={<PlayCircleOutlined />}
                      loading={crawlLoading}
                      onClick={() => onCrawl(config.id)}
                    >
                      Crawl
                    </Button>
                  )}
                  <Button icon={<EditOutlined />} onClick={() => setEditRecord(config)}>
                    Edit
                  </Button>
                  <Popconfirm title="Confirm delete this config?" onConfirm={() => onDelete(config.id)}>
                    <Button danger icon={<DeleteOutlined />}>
                      Delete
                    </Button>
                  </Popconfirm>
                </Space>
              </Card>
            </motion.div>
          ))}
        </Space>
        </motion.div>
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
