import { useState, useEffect } from 'react'
import { App, Table, Tag } from 'antd'
import { adminApi, type AuditLog } from '@/api/admin'

const ACTION_LABELS: Record<string, string> = {
  'user.create': '创建用户',
  'user.update': '更新用户',
  'user.delete': '删除用户',
  'user.register': '用户注册',
  'user.password_change': '修改密码',
  'user.wechat_bind': '绑定微信',
  'auth.login': '用户登录',
  'auth.logout': '用户登出',
  'product.update': '更新商品',
  'product.delete': '删除商品',
  'schedule.create': '创建定时配置',
  'schedule.update': '更新定时配置',
  'schedule.delete': '删除定时配置',
  'job_config.create': '创建职位配置',
  'job_config.update': '更新职位配置',
  'job_config.delete': '删除职位配置',
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
      message.error(error.response?.data?.detail || '获取审计日志失败')
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
      title: '操作',
      dataIndex: 'action',
      render: (action: string) => (
        <Tag color={ACTION_COLORS[action] || 'default'}>
          {ACTION_LABELS[action] || action}
        </Tag>
      ),
    },
    { title: '操作者ID', dataIndex: 'actor_user_id', width: 90 },
    { title: '目标类型', dataIndex: 'target_type' },
    { title: '目标ID', dataIndex: 'target_id' },
    {
      title: '详情',
      dataIndex: 'details',
      render: (details: Record<string, unknown> | null) =>
        details ? (
          <pre style={{ margin: 0, fontSize: 12, background: '#f7f7f5', padding: 4, borderRadius: 4 }}>
            {JSON.stringify(details, null, 2)}
          </pre>
        ) : null,
    },
    { title: 'IP地址', dataIndex: 'ip_address' },
    {
      title: '时间',
      dataIndex: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
  ]

  return (
    <div>
      <div className="page-header bg-surface-soft">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">系统管理</p>
            <h1 className="page-title">审计日志</h1>
            <p className="page-subtitle">查看系统操作审计记录</p>
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
          showTotal: (total) => `共 ${total} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />
    </div>
  )
}
