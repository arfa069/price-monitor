import { useState, useEffect } from 'react'
import { App, Table, Tag } from 'antd'
import { adminApi, type AuditLog } from '@/api/admin'

const ACTION_LABELS: Record<string, string> = {
  'user.create': 'Create User',
  'user.update': 'Update User',
  'user.delete': 'Delete User',
  'user.register': 'User Register',
  'user.password_change': 'Change Password',
  'user.wechat_bind': 'Bind WeChat',
  'auth.login': 'User Login',
  'auth.logout': 'User Logout',
  'product.update': 'Update Product',
  'product.delete': 'Delete Product',
  'schedule.create': 'Create Schedule',
  'schedule.update': 'Update Schedule',
  'schedule.delete': 'Delete Schedule',
  'job_config.create': 'Create Job Config',
  'job_config.update': 'Update Job Config',
  'job_config.delete': 'Delete Job Config',
}

const ACTION_COLORS: Record<string, string> = {
  'user.create': 'green',
  'user.update': 'blue',
  'user.delete': 'red',
  'user.register': 'cyan',
  'user.password_change': 'orange',
  'user.wechat_bind': 'cyan',
  'auth.login': 'purple',
  'auth.logout': 'default',
  'product.update': 'blue',
  'product.delete': 'red',
  'schedule.create': 'green',
  'schedule.update': 'blue',
  'schedule.delete': 'red',
  'job_config.create': 'green',
  'job_config.update': 'blue',
  'job_config.delete': 'red',
}

export default function AdminAuditLogsPage() {
  const message = App.useApp().message
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const response = await adminApi.getAuditLogs({ page, page_size: pageSize })
      setLogs(response.items)
      setTotal(response.total)
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to fetch audit logs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [page, pageSize])

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: 'Action',
      dataIndex: 'action',
      render: (action: string) => (
        <Tag color={ACTION_COLORS[action] || 'default'}>
          {ACTION_LABELS[action] || action}
        </Tag>
      ),
    },
    { title: 'Actor ID', dataIndex: 'actor_user_id', width: 90 },
    { title: 'Target Type', dataIndex: 'target_type' },
    { title: 'Target ID', dataIndex: 'target_id' },
    {
      title: 'Details',
      dataIndex: 'details',
      render: (details: Record<string, unknown> | null) =>
        details ? (
          <pre
            style={{
              margin: 0,
              fontSize: 12,
              background: 'var(--color-surface-soft)',
              color: 'var(--color-ink)',
              padding: 4,
              borderRadius: 4,
            }}
          >
            {JSON.stringify(details, null, 2)}
          </pre>
        ) : null,
    },
    { title: 'IP Address', dataIndex: 'ip_address' },
    {
      title: 'Time',
      dataIndex: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
  ]

  return (
    <div>
      <div className="page-header bg-admin-lilac">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">System Admin</p>
            <h1 className="page-title">Audit Logs</h1>
            <p className="page-subtitle">View system operation audit records</p>
          </div>
        </div>
      </div>

      <Table
        columns={columns}
        dataSource={logs}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} records`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />
    </div>
  )
}
