import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { App, Table, Button, Space, Modal, Form, Input, Select, Popconfirm, Switch, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { adminApi, type UserCreate, type UserUpdate } from '@/api/admin'
import { useAuth } from '@/contexts/AuthContext'
import { useStaggerAnimation } from '@/hooks/useStaggerAnimation'
import type { User } from '@/types'

type AdminApiError = {
  response?: {
    data?: {
      detail?: string
    }
  }
}

type UserFormValues = {
  username: string
  email: string
  password?: string
  role?: string
  is_active?: boolean
}

type FormValidationError = {
  errorFields?: unknown[]
}

function getAdminErrorMessage(error: unknown, fallback: string) {
  const detail = (error as AdminApiError).response?.data?.detail
  return detail || fallback
}

function isFormValidationError(error: unknown): error is FormValidationError {
  return Array.isArray((error as FormValidationError).errorFields)
}

export default function AdminUsersPage() {
  const message = App.useApp().message
  const { user: currentUser } = useAuth()
  const stagger = useStaggerAnimation(0.05, 0.05)
  const isSuperAdmin = currentUser?.role === 'super_admin'
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string | undefined>()

  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [form] = Form.useForm()

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const response = await adminApi.listUsers({ page, page_size: pageSize, search, role: roleFilter })
      setUsers(response.items)
      setTotal(response.total)
    } catch (error: unknown) {
      message.error(getAdminErrorMessage(error, '获取用户列表失败'))
    } finally {
      setLoading(false)
    }
  }, [message, page, pageSize, roleFilter, search])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchUsers()
  }, [fetchUsers])

  const handleCreate = () => {
    setEditingUser(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (user: User) => {
    setEditingUser(user)
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      role: user.role,
      is_active: user.is_active,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields() as UserFormValues
      if (editingUser) {
        const updateData: UserUpdate = {
          username: values.username,
          email: values.email,
          role: values.role,
          is_active: values.is_active,
        }
        await adminApi.updateUser(editingUser.id, updateData)
        message.success('用户已更新')
      } else {
        const createData: UserCreate = {
          username: values.username,
          email: values.email,
          password: values.password ?? '',
          role: values.role || 'user',
        }
        await adminApi.createUser(createData)
        message.success('用户已创建')
      }
      setModalOpen(false)
      fetchUsers()
    } catch (error: unknown) {
      if (!isFormValidationError(error)) {
        message.error(getAdminErrorMessage(error, '操作失败'))
      }
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await adminApi.deleteUser(id)
      message.success('用户已删除')
      fetchUsers()
    } catch (error: unknown) {
      message.error(getAdminErrorMessage(error, '删除失败'))
    }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username' },
    { title: '邮箱', dataIndex: 'email' },
    {
      title: '角色',
      dataIndex: 'role',
      render: (role: string) => {
        const map: Record<string, string> = { user: '普通用户', admin: '管理员', super_admin: '系统管理员' }
        return map[role] || role
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'error'}>
          {active ? '正常' : '已禁用'}
        </Tag>
      ),
    },
    { title: '注册时间', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() },
    {
      title: '操作',
      render: (_value: unknown, record: User) => {
        // Admin cannot edit/delete super_admin users
        const canEdit = isSuperAdmin || record.role !== 'super_admin'
        return (
          <Space size={4}>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              disabled={!canEdit}
            >
              编辑
            </Button>
            <Popconfirm
              title={`确定删除用户 ${record.username}？此操作不可恢复。`}
              onConfirm={() => handleDelete(record.id)}
              disabled={!canEdit}
            >
              <Button size="small" danger icon={<DeleteOutlined />} disabled={!canEdit}>删除</Button>
            </Popconfirm>
          </Space>
        )
      },
    },
  ]

  return (
    <div>
      {/* Page header — lilac for admin section (DESIGN.md: Lilac — 用户) */}
      <div className="page-header bg-admin">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">系统管理</p>
            <h1 className="page-title">用户管理</h1>
            <p className="page-subtitle">管理系统用户账号、角色与访问权限</p>
          </div>
        </div>
      </div>

      <motion.div variants={stagger.container} initial="hidden" animate="show">
        {/* Toolbar */}
        <motion.div variants={stagger.item} style={{ marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <Input.Search
            aria-label="搜索用户名或邮箱"
            placeholder="搜索用户名或邮箱"
            onSearch={setSearch}
            style={{ width: 200, fontFamily: 'var(--font-body)' }}
            className="fg-input"
          />
          <Select
            placeholder="筛选角色"
            allowClear
            style={{ width: 120, fontFamily: 'var(--font-body)' }}
            onChange={setRoleFilter}
            className="fg-select"
          >
            <Select.Option value="user">普通用户</Select.Option>
            <Select.Option value="admin">管理员</Select.Option>
          </Select>
          <Button
            icon={<PlusOutlined style={{ fontSize: 14 }} />}
            onClick={handleCreate}
            className="fg-btn-secondary"
          >
            新建用户
          </Button>
          <div style={{ flex: 1 }} />
        </motion.div>

        <motion.div variants={stagger.item}>
          <Table
            columns={columns}
            dataSource={users}
            rowKey="id"
            loading={loading}
            scroll={{ x: 'max-content' }}
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (p, ps) => { setPage(p); setPageSize(ps) },
            }}
          />
        </motion.div>
      </motion.div>

      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText={editingUser ? '保存' : '创建'}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, min: 3 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          {!editingUser && (
            <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="role" label="角色" initialValue="user">
            <Select>
              <Select.Option value="user">普通用户</Select.Option>
              <Select.Option value="admin">管理员</Select.Option>
              {isSuperAdmin && <Select.Option value="super_admin">系统管理员</Select.Option>}
            </Select>
          </Form.Item>
          {editingUser && (
            <Form.Item name="is_active" label="状态" valuePropName="checked">
              <Switch checkedChildren="正常" unCheckedChildren="禁用" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}
