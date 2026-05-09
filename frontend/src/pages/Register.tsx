import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, App, Typography } from 'antd'
import { UserOutlined, MailOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '@/api/auth'

const { Text } = Typography

interface RegisterFormValues {
  username: string
  email: string
  password: string
  password_confirm: string
}

export default function RegisterPage() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const message = App.useApp().message

  const handleSubmit = async (values: RegisterFormValues) => {
    if (values.password !== values.password_confirm) {
      message.error('两次输入的密码不一致')
      return
    }

    setLoading(true)
    try {
      await authApi.register({
        username: values.username,
        email: values.email,
        password: values.password,
        password_confirm: values.password_confirm,
      })
      message.success('注册成功！请登录')
      navigate('/login', { replace: true })
    } catch {
      message.error('注册失败，请检查输入信息')
      form.resetFields(['password', 'password_confirm'])
    } finally {
      setLoading(false)
    }
  }

  const validatePasswordConfirm = () => ({
    validator(_: unknown, value: string) {
      if (!value) return Promise.reject(new Error('请确认密码'))
      if (value !== form.getFieldValue('password'))
        return Promise.reject(new Error('两次输入的密码不一致'))
      return Promise.resolve()
    },
  })

  return (
    <div className="login-root">
      {/* Left Brand Panel */}
      <div className="login-brand">
        <div className="login-brand-inner">
          {/* Logo */}
          <div className="login-logo">
            <div className="login-logo-mark">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                <rect width="28" height="28" rx="7" fill="#000000" />
                <path
                  d="M8 14L12.5 18.5L20 9"
                  stroke="white"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <span className="login-logo-name">价格监控</span>
          </div>

          {/* Hero copy */}
          <div className="login-hero">
            <h1 className="login-headline">
              加入我们<br />
              开启监控
            </h1>
            <p className="login-subhead">
              创建账号，免费开始追踪全网商品价格<br />
              第一时间获取降价提醒
            </p>
          </div>

          {/* Feature pills */}
          <div className="login-features">
            <span className="feature-chip">免费使用</span>
            <span className="feature-chip">即时提醒</span>
            <span className="feature-chip">数据安全</span>
          </div>
        </div>

        {/* Decorative color block */}
        <div className="login-brand-decoration" />
      </div>

      {/* Right Form Panel */}
      <div className="login-form-panel">
        <div className="login-form-card">
          <div className="login-form-header">
            <h2 className="login-form-title">创建账号</h2>
            <p className="login-form-subtitle">加入价格监控系统</p>
          </div>

          <Form
            form={form}
            name="register"
            onFinish={handleSubmit}
            layout="vertical"
            requiredMark={false}
            className="login-form"
            initialValues={{ username: '', email: '', password: '', password_confirm: '' }}
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3个字符' },
                { max: 20, message: '用户名最多20个字符' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含字母、数字和下划线' },
              ]}
            >
              <Input
                prefix={<UserOutlined className="input-icon" />}
                placeholder="用户名"
                size="large"
                autoComplete="username"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input
                prefix={<MailOutlined className="input-icon" />}
                placeholder="邮箱"
                size="large"
                autoComplete="email"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
                { max: 50, message: '密码最多50个字符' },
              ]}
              hasFeedback
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="密码"
                size="large"
                autoComplete="new-password"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="password_confirm"
              rules={[
                { required: true, message: '请确认密码' },
                validatePasswordConfirm,
              ]}
              dependencies={['password']}
              hasFeedback
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="确认密码"
                size="large"
                autoComplete="new-password"
                className="login-input"
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                loading={loading}
                block
                className="login-btn-primary"
              >
                {loading ? '注册中...' : '注册'}
              </Button>
            </Form.Item>
          </Form>

          <div className="login-form-footer">
            <Text className="login-footer-text">已有账号？</Text>
            <Link to="/login" className="login-footer-link">
              立即登录
            </Link>
          </div>
        </div>

        <Text className="login-copyright">
          价格监控系统 © 2026
        </Text>
      </div>

      <style>{`
        .login-root {
          min-height: 100vh;
          display: flex;
          background: #ffffff;
        }

        .login-brand {
          flex: 1;
          background: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 48px;
          position: relative;
          overflow: hidden;
        }

        .login-brand-inner {
          max-width: 480px;
          width: 100%;
          z-index: 1;
        }

        .login-logo {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 64px;
        }

        .login-logo-mark {
          animation: scaleIn 0.5s ease-out 0.1s both;
        }

        .login-logo-name {
          font-family: 'Inter', system-ui, sans-serif;
          font-size: 18px;
          font-weight: 480;
          color: #000000;
          letter-spacing: -0.2px;
        }

        .login-headline {
          font-family: 'Inter', system-ui, sans-serif;
          font-size: clamp(40px, 5vw, 64px);
          font-weight: 340;
          line-height: 1.05;
          letter-spacing: -1.72px;
          color: #000000;
          margin: 0 0 24px 0;
          animation: fadeUp 0.6s ease-out 0.2s both;
        }

        .login-subhead {
          font-family: 'Inter', system-ui, sans-serif;
          font-size: 18px;
          font-weight: 320;
          line-height: 1.6;
          color: #000000;
          margin: 0 0 40px 0;
          animation: fadeUp 0.6s ease-out 0.35s both;
        }

        .login-features {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          animation: fadeUp 0.6s ease-out 0.5s both;
        }

        .feature-chip {
          font-family: 'JetBrains Mono', monospace;
          font-size: 12px;
          font-weight: 400;
          letter-spacing: 0.6px;
          text-transform: uppercase;
          color: #000000;
          background: #f7f7f5;
          border: 1px solid #e6e6e6;
          border-radius: 50px;
          padding: 6px 14px;
        }

        .login-brand-decoration {
          position: absolute;
          right: -60px;
          top: 50%;
          transform: translateY(-50%) rotate(-4deg);
          width: 320px;
          height: 320px;
          background: #c5b0f4;
          border-radius: 24px;
          z-index: 0;
        }

        .login-form-panel {
          width: 480px;
          min-width: 380px;
          background: #f7f7f5;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 48px 40px;
          gap: 24px;
        }

        .login-form-card {
          width: 100%;
          max-width: 360px;
          background: #ffffff;
          border-radius: 24px;
          padding: 40px;
          border: 1px solid #e6e6e6;
          animation: fadeUp 0.6s ease-out 0.2s both;
        }

        .login-form-header {
          margin-bottom: 32px;
        }

        .login-form-title {
          font-family: 'Inter', system-ui, sans-serif;
          font-size: 26px;
          font-weight: 540;
          line-height: 1.35;
          letter-spacing: -0.26px;
          color: #000000;
          margin: 0 0 6px 0;
        }

        .login-form-subtitle {
          font-family: 'Inter', system-ui, sans-serif;
          font-size: 16px;
          font-weight: 330;
          color: #666666;
          margin: 0;
        }

        .login-form {
          animation: fadeUp 0.6s ease-out 0.35s both;
        }

        .login-form .ant-form-item {
          margin-bottom: 16px;
        }

        .login-form .ant-form-item-label > label {
          font-family: 'Inter', system-ui, sans-serif;
          font-size: 14px;
          font-weight: 330;
          color: #000000;
          line-height: 1.45;
          padding-bottom: 6px;
        }

        .login-input .ant-input {
          padding: 11px 14px !important;
          border-radius: 8px !important;
          border: 1px solid #e6e6e6 !important;
          font-family: 'Inter', system-ui, sans-serif !important;
          font-size: 16px !important;
          font-weight: 320 !important;
          background: #ffffff !important;
          transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        .login-input .ant-input:hover {
          border-color: #999 !important;
        }

        .login-input .ant-input:focus {
          border-color: #000000 !important;
          box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.06) !important;
        }

        .login-input .ant-input-affix-wrapper {
          padding: 11px 14px !important;
          border-radius: 8px !important;
          border: 1px solid #e6e6e6 !important;
          background: #ffffff !important;
          transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        .login-input .ant-input-affix-wrapper:hover {
          border-color: #999 !important;
        }

        .login-input .ant-input-affix-wrapper:focus,
        .login-input .ant-input-affix-wrapper-focused {
          border-color: #000000 !important;
          box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.06) !important;
        }

        .input-icon {
          color: #999;
          font-size: 14px;
          transition: color 0.2s ease;
        }

        .login-input .ant-input:focus ~ .ant-input-suffix .input-icon,
        .login-input:hover .input-icon {
          color: #000000;
        }

        .login-btn-primary {
          height: auto !important;
          padding: 12px 24px !important;
          border-radius: 50px !important;
          font-family: 'Inter', system-ui, sans-serif !important;
          font-size: 16px !important;
          font-weight: 480 !important;
          letter-spacing: -0.1px !important;
          background: #000000 !important;
          border: none !important;
          color: #ffffff !important;
          width: 100%;
          transition: background 0.2s ease, transform 0.15s ease !important;
          margin-top: 8px;
        }

        .login-btn-primary:hover:not(:disabled) {
          background: #222222 !important;
          transform: translateY(-1px);
        }

        .login-btn-primary:active:not(:disabled) {
          transform: translateY(0);
        }

        .login-btn-primary:disabled {
          opacity: 0.6;
        }

        .login-form-footer {
          text-align: center;
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid #f1f1f1;
          animation: fadeUp 0.6s ease-out 0.5s both;
        }

        .login-footer-text {
          font-family: 'Inter', system-ui, sans-serif !important;
          font-size: 14px !important;
          font-weight: 330 !important;
          color: #666666 !important;
        }

        .login-footer-link {
          font-family: 'Inter', system-ui, sans-serif !important;
          font-size: 14px !important;
          font-weight: 480 !important;
          color: #000000 !important;
          transition: opacity 0.2s ease;
          padding: 4px 8px;
          border-radius: 50px;
        }

        .login-footer-link:hover {
          background: #f7f7f5;
          opacity: 0.8;
        }

        .login-copyright {
          font-family: 'JetBrains Mono', monospace !important;
          font-size: 11px !important;
          font-weight: 400 !important;
          letter-spacing: 0.6px !important;
          text-transform: uppercase !important;
          color: #999 !important;
          animation: fadeUp 0.6s ease-out 0.6s both;
        }

        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.85); }
          to { opacity: 1; transform: scale(1); }
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @media (max-width: 768px) {
          .login-root {
            flex-direction: column;
          }

          .login-brand {
            flex: none;
            padding: 40px 24px 32px;
            min-height: auto;
          }

          .login-brand-decoration {
            display: none;
          }

          .login-logo {
            margin-bottom: 32px;
          }

          .login-form-panel {
            width: 100%;
            min-width: 0;
            padding: 32px 24px 40px;
          }
        }
      `}</style>
    </div>
  )
}
