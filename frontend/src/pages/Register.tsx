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
      message.error('Passwords do not match')
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
      message.success('Registration successful! Please sign in')
      navigate('/login', { replace: true })
    } catch {
      message.error('Registration failed, please check your input')
      form.resetFields(['password', 'password_confirm'])
    } finally {
      setLoading(false)
    }
  }

  const validatePasswordConfirm = () => ({
    validator(_: unknown, value: string) {
      if (!value) return Promise.reject(new Error('Please confirm password'))
      if (value !== form.getFieldValue('password'))
        return Promise.reject(new Error('Passwords do not match'))
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
            <span className="login-logo-name">Price Monitor</span>
          </div>

          {/* Hero copy */}
          <div className="login-hero">
            <h1 className="login-headline">
              Join Us<br />
              Start Monitoring
            </h1>
            <p className="login-subhead">
              Create an account and start tracking prices for free<br />
              Get price drop alerts instantly
            </p>
          </div>

          {/* Feature pills */}
          <div className="login-features">
            <span className="feature-chip">Free to Use</span>
            <span className="feature-chip">Instant Alerts</span>
            <span className="feature-chip">Data Secure</span>
          </div>
        </div>

        {/* Decorative color block */}
        <div className="login-brand-decoration" />
      </div>

      {/* Right Form Panel */}
      <div className="login-form-panel">
        <div className="login-form-card">
          <div className="login-form-header">
            <h2 className="login-form-title">Create Account</h2>
            <p className="login-form-subtitle">Join Price Monitor</p>
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
                { required: true, message: 'Please enter username' },
                { min: 3, message: 'Username must be at least 3 characters' },
                { max: 20, message: 'Username must be no more than 20 characters' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: 'Only letters, numbers, and underscores allowed' },
              ]}
            >
              <Input
                prefix={<UserOutlined className="input-icon" />}
                placeholder="Username"
                size="large"
                autoComplete="username"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: 'Please enter email' },
                { type: 'email', message: 'Please enter a valid email address' },
              ]}
            >
              <Input
                prefix={<MailOutlined className="input-icon" />}
                placeholder="Email"
                size="large"
                autoComplete="email"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: 'Please enter password' },
                { min: 6, message: 'Password must be at least 6 characters' },
                { max: 50, message: 'Password must be no more than 50 characters' },
              ]}
              hasFeedback
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="Password"
                size="large"
                autoComplete="new-password"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="password_confirm"
              rules={[
                { required: true, message: 'Please confirm password' },
                validatePasswordConfirm,
              ]}
              dependencies={['password']}
              hasFeedback
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="Confirm Password"
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
                {loading ? 'Creating account...' : 'Sign Up'}
              </Button>
            </Form.Item>
          </Form>

          <div className="login-form-footer">
            <Text className="login-footer-text">Already have an account?</Text>
            <Link to="/login" className="login-footer-link">
              Sign In
            </Link>
          </div>
        </div>

        <Text className="login-copyright">
          Price Monitor © 2026
        </Text>
      </div>

      <style>{`
        .login-root {
          min-height: 100vh;
          display: flex;
          background: var(--color-canvas);
        }

        .login-brand {
          flex: 1;
          background: var(--color-canvas);
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
          animation: fadeInUp 150ms ease-out 50ms both;
        }

        .login-logo-name {
          font-family: var(--font-body);
          font-size: 18px;
          font-weight: 480;
          color: var(--color-ink);
          letter-spacing: -0.2px;
        }

        .login-headline {
          font-family: var(--font-display);
          font-size: clamp(40px, 5vw, 64px);
          font-weight: 340;
          line-height: 1.05;
          letter-spacing: -1.72px;
          color: var(--color-ink);
          margin: 0 0 24px 0;
          animation: fadeInUp 150ms ease-out 100ms both;
        }

        .login-subhead {
          font-family: var(--font-body);
          font-size: 18px;
          font-weight: 320;
          line-height: 1.6;
          color: var(--color-ink);
          margin: 0 0 40px 0;
          animation: fadeInUp 150ms ease-out 150ms both;
        }

        .login-features {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          animation: fadeInUp 150ms ease-out 200ms both;
        }

        .feature-chip {
          font-family: 'JetBrains Mono', monospace;
          font-size: 12px;
          font-weight: 400;
          letter-spacing: 0.6px;
          text-transform: uppercase;
          color: var(--color-ink);
          background: var(--color-surface-soft);
          border: 1px solid var(--color-hairline);
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
          background: var(--color-block-lilac);
          border-radius: 24px;
          z-index: 0;
        }

        .login-form-panel {
          width: 480px;
          min-width: 380px;
          background: var(--color-surface-soft);
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
          background: var(--color-canvas);
          border-radius: 24px;
          padding: 40px;
          border: 1px solid var(--color-hairline);
          animation: fadeInUp 150ms ease-out 100ms both;
        }

        .login-form-header {
          margin-bottom: 32px;
        }

        .login-form-title {
          font-family: var(--font-display);
          font-size: 26px;
          font-weight: 540;
          line-height: 1.35;
          letter-spacing: -0.26px;
          color: var(--color-ink);
          margin: 0 0 6px 0;
        }

        .login-form-subtitle {
          font-family: var(--font-body);
          font-size: 16px;
          font-weight: 330;
          color: var(--color-muted);
          margin: 0;
        }

        .login-form {
          animation: fadeInUp 150ms ease-out 150ms both;
        }

        .login-form .ant-form-item {
          margin-bottom: 16px;
        }

        .login-form .ant-form-item-label > label {
          font-family: var(--font-body);
          font-size: 14px;
          font-weight: 330;
          color: var(--color-ink);
          line-height: 1.45;
          padding-bottom: 6px;
        }

        .login-input .ant-input {
          padding: 11px 14px !important;
          border-radius: 8px !important;
          border: 1px solid var(--color-hairline) !important;
          font-family: var(--font-body) !important;
          font-size: 16px !important;
          font-weight: 320 !important;
          background: var(--color-canvas) !important;
          transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        .login-input .ant-input:hover {
          border-color: var(--color-border-hover) !important;
        }

        .login-input .ant-input:focus {
          border-color: var(--color-primary) !important;
          box-shadow: 0 0 0 3px var(--color-focus-ring) !important;
        }

        .login-input .ant-input-affix-wrapper {
          padding: 11px 14px !important;
          border-radius: 8px !important;
          border: 1px solid var(--color-hairline) !important;
          background: var(--color-canvas) !important;
          transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        .login-input .ant-input-affix-wrapper:hover {
          border-color: var(--color-border-hover) !important;
        }

        .login-input .ant-input-affix-wrapper:focus,
        .login-input .ant-input-affix-wrapper-focused {
          border-color: var(--color-primary) !important;
          box-shadow: 0 0 0 3px var(--color-focus-ring) !important;
        }

        .input-icon {
          color: var(--color-muted);
          font-size: 14px;
          transition: color 0.2s ease;
        }

        .login-input .ant-input:focus ~ .ant-input-suffix .input-icon,
        .login-input:hover .input-icon {
          color: var(--color-ink);
        }

        .login-btn-primary {
          height: auto !important;
          padding: 12px 24px !important;
          border-radius: 50px !important;
          font-family: var(--font-body) !important;
          font-size: 16px !important;
          font-weight: 480 !important;
          letter-spacing: -0.1px !important;
          background: var(--color-primary) !important;
          border: none !important;
          color: var(--color-on-primary) !important;
          width: 100%;
          transition: background 0.2s ease, transform 0.15s ease !important;
          margin-top: 8px;
        }

        .login-btn-primary:hover:not(:disabled) {
          background: var(--color-primary-hover) !important;
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
          border-top: 1px solid var(--color-hairline-soft);
          animation: fadeInUp 150ms ease-out 200ms both;
        }

        .login-footer-text {
          font-family: var(--font-body) !important;
          font-size: 14px !important;
          font-weight: 330 !important;
          color: var(--color-muted) !important;
        }

        .login-footer-link {
          font-family: var(--font-body) !important;
          font-size: 14px !important;
          font-weight: 480 !important;
          color: var(--color-ink) !important;
          transition: opacity 0.2s ease;
          padding: 4px 8px;
          border-radius: 50px;
        }

        .login-footer-link:hover {
          background: var(--color-surface-soft);
          opacity: 0.8;
        }

        .login-copyright {
          font-family: 'JetBrains Mono', monospace !important;
          font-size: 11px !important;
          font-weight: 400 !important;
          letter-spacing: 0.6px !important;
          text-transform: uppercase !important;
          color: var(--color-muted) !important;
          animation: fadeInUp 150ms ease-out 250ms both;
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
