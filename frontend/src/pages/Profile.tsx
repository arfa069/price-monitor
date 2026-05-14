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
      message.success('Profile updated successfully')
      window.location.reload()
    } catch (error: unknown) {
      const axiosError = error as AxiosError<{ detail?: string }>
      message.error(axiosError.response?.data?.detail || 'Update failed')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordChange = async (values: { old_password: string; new_password: string }) => {
    setLoading(true)
    try {
      await authApi.changePassword(values)
      message.success('Password changed successfully')
      passwordForm.resetFields()
    } catch (error: unknown) {
      const axiosError = error as AxiosError<{ detail?: string }>
      message.error(axiosError.response?.data?.detail || 'Change failed')
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
            <p className="page-eyebrow">Account</p>
            <h1 className="page-title">Personal Info</h1>
            <p className="page-subtitle">View and edit your account information</p>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 560, marginTop: 24 }}>
        {/* Info card */}
        <div className="fg-card" style={{ marginBottom: 16 }}>
          <div className="fg-card-header">
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
              Account Info
            </span>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <Descriptions column={1}>
              <Descriptions.Item label="Username">{user.username}</Descriptions.Item>
              <Descriptions.Item label="Email">{user.email}</Descriptions.Item>
              <Descriptions.Item label="Role">{user.role === 'user' ? 'Regular User' : user.role === 'admin' ? 'Admin' : 'System Admin'}</Descriptions.Item>
              <Descriptions.Item label="Registered">{user.created_at ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(user.created_at)) : '-'}</Descriptions.Item>
            </Descriptions>
          </div>
        </div>

        {/* Edit profile card */}
        <div className="fg-card" style={{ marginBottom: 16 }}>
          <div className="fg-card-header">
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
              Edit Personal Info
            </span>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{ username: user.username, email: user.email }}
              onFinish={handleProfileUpdate}
            >
              <Form.Item name="username" label="Username" rules={[{ required: true, min: 3, max: 50 }]}>
                <Input style={{ fontFamily: 'var(--font-body)' }} autoComplete="username" />
              </Form.Item>
              <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
                <Input style={{ fontFamily: 'var(--font-body)' }} autoComplete="email" />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={loading} className="fg-btn-primary">
                  Save
                </Button>
              </Form.Item>
            </Form>
          </div>
        </div>

        {/* Password card */}
        <div className="fg-card">
          <div className="fg-card-header">
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 15, fontWeight: 480, color: 'var(--color-ink)' }}>
              Change Password
            </span>
          </div>
          <div style={{ padding: '20px 24px' }}>
            <Form form={passwordForm} layout="vertical" onFinish={handlePasswordChange}>
              <Form.Item name="old_password" label="Current Password" rules={[{ required: true }]}>
                <Input.Password style={{ fontFamily: 'var(--font-body)' }} autoComplete="current-password" />
              </Form.Item>
              <Form.Item name="new_password" label="New Password" rules={[{ required: true, min: 6 }]}>
                <Input.Password style={{ fontFamily: 'var(--font-body)' }} autoComplete="new-password" />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={loading} className="fg-btn-primary">
                  Change Password
                </Button>
              </Form.Item>
            </Form>
          </div>
        </div>
      </div>
    </div>
  )
}
