import { useState } from 'react'
import { Card, Form, Input, Button, App, Descriptions } from 'antd'
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
    <div style={{ maxWidth: 600 }}>
      <Card title="个人信息" style={{ marginBottom: 16 }}>
        <Descriptions column={1}>
          <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
          <Descriptions.Item label="角色">{user.role === 'user' ? '普通用户' : user.role === 'admin' ? '管理员' : '系统管理员'}</Descriptions.Item>
          <Descriptions.Item label="注册时间">{user.created_at ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(user.created_at)) : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="修改个人信息" style={{ marginBottom: 16 }}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{ username: user.username, email: user.email }}
          onFinish={handleProfileUpdate}
        >
          <Form.Item name="username" label="用户名" rules={[{ required: true, min: 3, max: 50 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="修改密码">
        <Form form={passwordForm} layout="vertical" onFinish={handlePasswordChange}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
