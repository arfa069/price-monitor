import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Form, Input, Button, message, Typography } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '@/api/auth'
import { useAuth } from '@/contexts/AuthContext'

const { Title, Text } = Typography

interface LoginFormValues {
  username: string
  password: string
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  // 获取之前尝试访问的页面，登录后跳转回去
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/jobs'

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      const response = await authApi.login({
        username: values.username,
        password: values.password,
      })

      const { access_token } = response.data

      // 先保存 token，让后续请求能携带 token
      login(access_token, { id: 0, username: '', email: '' })

      // 获取用户信息
      const meResponse = await authApi.getMe()
      const user = meResponse.data

      // 更新用户信息
      login(access_token, { id: user.id, username: user.username, email: user.email })

      message.success(`欢迎回来，${user.username}！`)

      // 跳转到之前页面或首页
      navigate(from, { replace: true })
    } catch {
      message.error('用户名或密码错误')
      form.resetFields(['password'])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-background">
        <div className="auth-glow auth-glow-1" />
        <div className="auth-glow auth-glow-2" />
        <div className="auth-pattern" />
      </div>

      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="10" fill="url(#logoGradient)" />
                <path
                  d="M12 20L18 26L28 14"
                  stroke="white"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <defs>
                  <linearGradient id="logoGradient" x1="0" y1="0" x2="40" y2="40">
                    <stop stopColor="#0ea5e9" />
                    <stop offset="1" stopColor="#1e3a5f" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <Title level={3} className="auth-title">欢迎回来</Title>
            <Text type="secondary" className="auth-subtitle">
              登录到价格监控系统
            </Text>
          </div>

          <Form
            form={form}
            name="login"
            onFinish={handleSubmit}
            layout="vertical"
            requiredMark={false}
            className="auth-form"
            initialValues={{ username: '', password: '' }}
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名或邮箱' },
                { min: 2, message: '用户名至少2个字符' },
              ]}
            >
              <Input
                prefix={<UserOutlined className="input-icon" />}
                placeholder="用户名或邮箱"
                size="large"
                autoComplete="username"
                className="auth-input"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="密码"
                size="large"
                autoComplete="current-password"
                className="auth-input"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                loading={loading}
                block
                className="auth-button"
              >
                {loading ? '登录中...' : '登录'}
              </Button>
            </Form.Item>
          </Form>

          <div className="auth-footer">
            <Text type="secondary">
              还没有账号？{' '}
              <Link to="/register" className="auth-link">
                立即注册
              </Link>
            </Text>
          </div>
        </div>

        <Text type="secondary" className="auth-copyright">
          价格监控系统 © 2026
        </Text>
      </div>

      <style>{`
        .auth-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 50%, #cbd5e1 100%);
          position: relative;
          overflow: hidden;
        }

        .auth-background {
          position: absolute;
          inset: 0;
          pointer-events: none;
        }

        .auth-glow {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.4;
        }

        .auth-glow-1 {
          width: 400px;
          height: 400px;
          background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%);
          top: -100px;
          right: -100px;
          animation: float 8s ease-in-out infinite;
        }

        .auth-glow-2 {
          width: 300px;
          height: 300px;
          background: linear-gradient(135deg, #1e3a5f 0%, #3b82f6 100%);
          bottom: -50px;
          left: -50px;
          animation: float 10s ease-in-out infinite reverse;
        }

        .auth-pattern {
          position: absolute;
          inset: 0;
          background-image:
            radial-gradient(circle at 25% 25%, rgba(14, 165, 233, 0.05) 0%, transparent 50%),
            radial-gradient(circle at 75% 75%, rgba(30, 58, 95, 0.05) 0%, transparent 50%);
        }

        @keyframes float {
          0%, 100% { transform: translate(0, 0); }
          50% { transform: translate(20px, -20px); }
        }

        .auth-container {
          position: relative;
          z-index: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 20px;
          animation: slideUp 0.6s ease-out;
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .auth-card {
          background: white;
          border-radius: 16px;
          padding: 40px;
          width: 100%;
          max-width: 400px;
          box-shadow:
            0 4px 6px -1px rgba(0, 0, 0, 0.1),
            0 2px 4px -2px rgba(0, 0, 0, 0.1),
            0 0 0 1px rgba(0, 0, 0, 0.05);
        }

        .auth-header {
          text-align: center;
          margin-bottom: 32px;
        }

        .auth-logo {
          margin-bottom: 20px;
          animation: scaleIn 0.5s ease-out 0.2s both;
        }

        @keyframes scaleIn {
          from {
            opacity: 0;
            transform: scale(0.8);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .auth-title {
          margin: 0 0 8px 0 !important;
          color: #1e3a5f !important;
          animation: fadeIn 0.5s ease-out 0.3s both;
        }

        .auth-subtitle {
          display: block;
          animation: fadeIn 0.5s ease-out 0.4s both;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .auth-form {
          animation: fadeIn 0.5s ease-out 0.5s both;
        }

        .auth-input .ant-input {
          padding-left: 40px !important;
          border-radius: 10px !important;
          border-color: #e2e8f0 !important;
          transition: all 0.3s ease !important;
        }

        .auth-input .ant-input:hover {
          border-color: #94a3b8 !important;
        }

        .auth-input .ant-input:focus {
          border-color: #0ea5e9 !important;
          box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1) !important;
        }

        .auth-input .ant-input-affix-wrapper {
          padding-left: 40px !important;
          border-radius: 10px !important;
          border-color: #e2e8f0 !important;
          transition: all 0.3s ease !important;
        }

        .auth-input .ant-input-affix-wrapper:hover {
          border-color: #94a3b8 !important;
        }

        .auth-input .ant-input-affix-wrapper:focus,
        .auth-input .ant-input-affix-wrapper-focused {
          border-color: #0ea5e9 !important;
          box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1) !important;
        }

        .input-icon {
          color: #94a3b8;
          transition: color 0.3s ease;
        }

        .auth-input .ant-input:focus + .ant-input-suffix .input-icon,
        .auth-input .ant-input-focused + .ant-input-suffix .input-icon,
        .auth-input:hover .input-icon {
          color: #0ea5e9;
        }

        .auth-button {
          height: 48px !important;
          border-radius: 10px !important;
          font-size: 16px !important;
          font-weight: 500 !important;
          background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
          border: none !important;
          box-shadow: 0 4px 14px rgba(14, 165, 233, 0.4) !important;
          transition: all 0.3s ease !important;
        }

        .auth-button:hover:not(:disabled) {
          background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%) !important;
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(14, 165, 233, 0.5) !important;
        }

        .auth-button:active:not(:disabled) {
          transform: translateY(0);
        }

        .auth-button:disabled {
          opacity: 0.7;
        }

        .auth-footer {
          text-align: center;
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid #f1f5f9;
          animation: fadeIn 0.5s ease-out 0.6s both;
        }

        .auth-link {
          color: #0ea5e9 !important;
          font-weight: 500;
          transition: color 0.3s ease;
        }

        .auth-link:hover {
          color: #0284c7 !important;
        }

        .auth-copyright {
          margin-top: 24px;
          font-size: 12px;
          animation: fadeIn 0.5s ease-out 0.7s both;
        }
      `}</style>
    </div>
  )
}
