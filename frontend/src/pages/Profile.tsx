import { useState } from 'react'
import { Form, Input, Button, App, Descriptions } from 'antd'
import type { AxiosError } from 'axios'
import { useAuth } from '@/contexts/AuthContext'
import { authApi } from '@/api/auth'

export default function ProfilePage() {
  const { user } = useAuth()
  const [form] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const message = App.useApp().message

  const handleProfileUpdate = async (values: { username: string; email: string }) => {
    setLoading(true)
    try {
      await authApi.updateProfile(values)
      message.success('个人信息已更新')
      window.location.reload()
    } catch (error: unknown) {
      const axiosError = error as AxiosError<{ detail?: string }>
      message.error(axiosError.response?.data?.detail || '更新失败')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordChange = async (values: { old_password: string; new_password: string }) => {
    setLoading(true)
    try {
      await authApi.changePassword(values)
      message.success('密码已修改')
      passwordForm.resetFields()
    } catch (error: unknown) {
      const axiosError = error as AxiosError<{ detail?: string }>
      message.error(axiosError.response?.data?.detail || '修改失败')
    } finally {
      setLoading(false)
    }
  }

  if (!user) return null

  return (
    <div>
      {/* Page header — cream color block */}
      <div className="page-header bg-cream">
        <div className="page-header-inner">
          <div>
            <p className="page-eyebrow">账户</p>
            <h1 className="page-title">个人信息</h1>
            <p className="page-subtitle">查看和修改您的账户信息</p>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 560, marginTop: 24 }}>
        {/* Info card */}
        <div className="fg-card" style={{ marginBottom: 16 }}>
          <div className="fg-card-header">
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
              账户信息
            </span>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <Descriptions column={1}>
              <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
              <Descriptions.Item label="角色">{user.role === 'user' ? '普通用户' : user.role === 'admin' ? '管理员' : '系统管理员'}</Descriptions.Item>
              <Descriptions.Item label="注册时间">{user.created_at ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(user.created_at)) : '-'}</Descriptions.Item>
            </Descriptions>
          </div>
        </div>

        {/* Edit profile card */}
        <div className="fg-card" style={{ marginBottom: 16 }}>
          <div className="fg-card-header">
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
              修改个人信息
            </span>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{ username: user.username, email: user.email }}
              onFinish={handleProfileUpdate}
            >
              <Form.Item name="username" label="用户名" rules={[{ required: true, min: 3, max: 50 }]}>
                <Input style={{ fontFamily: 'var(--font-body)' }} />
              </Form.Item>
              <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
                <Input style={{ fontFamily: 'var(--font-body)' }} />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={loading} className="fg-btn-primary">
                  保存
                </Button>
              </Form.Item>
            </Form>
          </div>
        </div>

        {/* Password card */}
        <div className="fg-card">
          <div className="fg-card-header">
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
              修改密码
            </span>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <Form form={passwordForm} layout="vertical" onFinish={handlePasswordChange}>
              <Form.Item name="old_password" label="原密码" rules={[{ required: true }]}>
                <Input.Password style={{ fontFamily: 'var(--font-body)' }} />
              </Form.Item>
              <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6 }]}>
                <Input.Password style={{ fontFamily: 'var(--font-body)' }} />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={loading} className="fg-btn-primary">
                  修改密码
                </Button>
              </Form.Item>
            </Form>
          </div>
        </div>
      </div>
    </div>
  )
}
