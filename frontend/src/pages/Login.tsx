import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Form, Input, Button, App, Typography } from 'antd'
import { authApi } from '@/api/auth'
import { useAuth } from '@/contexts/AuthContext'

const { Text } = Typography

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
  const message = App.useApp().message

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/jobs'

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      const response = await authApi.login({
        username: values.username,
        password: values.password,
      })
      const { access_token } = response.data
      login(access_token, { id: 0, username: '', email: '', role: 'user' as const })

      const meResponse = await authApi.getMe()
      const user = meResponse.data
      login(access_token, {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role || 'user',
      })

      message.success(`欢迎回来，${user.username}！`)
      navigate(from, { replace: true })
    } catch {
      message.error('用户名或密码错误')
      form.resetFields(['password'])
    } finally {
      setLoading(false)
    }
  }

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
              全网价格<br />
              一站掌控
            </h1>
            <p className="login-subhead">
              实时追踪淘宝、京东、亚马逊商品价格<br />
              降价自动推送，不错过任何优惠
            </p>
          </div>
        </div>

        {/* Decorative color block */}
        <div className="login-brand-decoration" />
      </div>

      {/* Right Form Panel */}
      <div className="login-form-panel">
        <div className="login-form-card">
          <div className="login-form-header">
            <h2 className="login-form-title">欢迎回来</h2>
            <p className="login-form-subtitle">登录到价格监控系统</p>
          </div>

          <Form
            form={form}
            name="login"
            onFinish={handleSubmit}
            layout="vertical"
            requiredMark={false}
            className="login-form"
            initialValues={{ username: '', password: '' }}
          >
            <Form.Item
              name="username"
              label="邮箱"
              rules={[
                { required: true, message: '请输入用户名或邮箱' },
                { min: 2, message: '用户名至少2个字符' },
              ]}
            >
              <Input
                placeholder="user@example.com"
                size="large"
                autoComplete="username"
                className="login-input"
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="密码"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6个字符' },
              ]}
            >
              <Input.Password
                placeholder="••••••••"
                size="large"
                autoComplete="current-password"
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
                {loading ? '登录中...' : '登录'}
              </Button>
            </Form.Item>
          </Form>

          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Button
              disabled
              size="large"
              block
              style={{
                borderRadius: 50,
                background: 'var(--color-surface-soft)',
                borderColor: 'var(--color-hairline)',
                color: 'var(--color-muted)',
                fontFamily: 'var(--font-body)',
              }}
            >
              微信登录（暂不可用）
            </Button>
          </div>

          <div className="login-form-footer">
            <Text className="login-footer-text">
              还没有账号？{' '}
            </Text>
            <Link to="/register" className="login-footer-link">
              立即注册
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
          background: var(--color-canvas);
        }

        /* ---- Left Brand Panel ---- */
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

        /* Logo */
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
          font-family: var(--font-body);
          font-size: 18px;
          font-weight: 480;
          color: var(--color-ink);
          letter-spacing: -0.2px;
        }

        /* Hero */
        .login-headline {
          font-family: var(--font-display);
          font-size: clamp(40px, 5vw, 64px);
          font-weight: 340;
          line-height: 1.05;
          letter-spacing: -1.72px;
          color: var(--color-ink);
          margin: 0 0 24px 0;
          animation: fadeUp 0.6s ease-out 0.2s both;
        }

        .login-subhead {
          font-family: var(--font-body);
          font-size: 18px;
          font-weight: 320;
          line-height: 1.6;
          color: var(--color-ink);
          margin: 0 0 40px 0;
          animation: fadeUp 0.6s ease-out 0.35s both;
        }

        /* Decorative color block — lime accent strip (DESIGN.md: Login Mockup) */
        .login-brand-decoration {
          position: absolute;
          right: -20px;
          top: 50%;
          transform: translateY(-50%);
          width: 80px;
          height: 200px;
          background: var(--color-block-lime);
          border-radius: var(--radius-lg);
          z-index: 0;
        }

        /* ---- Right Form Panel ---- */
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
          background: var(--color-surface-raised);
          border-radius: 24px;
          padding: 40px;
          box-shadow: var(--shadow-card);
          animation: fadeUp 0.6s ease-out 0.2s both;
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
          animation: fadeUp 0.6s ease-out 0.35s both;
        }

        /* Form items */
        .login-form .ant-form-item {
          margin-bottom: 20px;
        }

        .login-form .ant-form-item-label > label {
          font-family: var(--font-body);
          font-size: 12px;
          font-weight: 500;
          color: var(--color-muted);
          letter-spacing: 0.3px;
          line-height: 1.4;
          height: auto;
          padding-bottom: 6px;
        }

        .login-input .ant-input {
          padding: 11px 14px !important;
          border-radius: 8px !important;
          border: 1px solid var(--color-hairline) !important;
          font-family: var(--font-body) !important;
          font-size: 16px !important;
          font-weight: 320 !important;
          background: var(--color-surface-soft) !important;
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
          background: var(--color-surface-soft) !important;
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

        /* Inner input inside affix-wrapper (e.g. Input.Password) — keep transparent so only wrapper shows the frame */
        .login-input.ant-input-affix-wrapper .ant-input,
        .login-input .ant-input-affix-wrapper .ant-input {
          background: transparent !important;
          border: none !important;
          padding: 0 !important;
          box-shadow: none !important;
          font-size: 16px !important;
          font-weight: 320 !important;
        }

        /* Override browser autofill (Chrome/Edge/Safari) blue/yellow tint */
        .login-input input:-webkit-autofill,
        .login-input input:-webkit-autofill:hover,
        .login-input input:-webkit-autofill:focus,
        .login-input input:-webkit-autofill:active {
          -webkit-box-shadow: 0 0 0 1000px var(--color-surface-soft) inset !important;
          -webkit-text-fill-color: var(--color-ink) !important;
          caret-color: var(--color-ink) !important;
          transition: background-color 5000s ease-in-out 0s !important;
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

        /* Primary pill button */
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
          margin-top: 4px;
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

        /* Footer */
        .login-form-footer {
          text-align: center;
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid var(--color-hairline-soft);
          animation: fadeUp 0.6s ease-out 0.5s both;
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
          animation: fadeUp 0.6s ease-out 0.6s both;
        }

        /* Animations */
        @keyframes scaleIn {
          from { opacity: 0; transform: scale(0.85); }
          to { opacity: 1; transform: scale(1); }
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }

        /* Responsive */
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
