import { type ReactNode } from 'react'
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { App as AntdApp, ConfigProvider, Spin, theme } from 'antd'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import AppLayout from '@/components/AppLayout'
import { ThemeProvider, useThemeContext } from '@/components/ThemeProvider'
import JobsPage from '@/pages/JobsPage'
import ProductsPage from '@/pages/ProductsPage'
import ScheduleConfigPage from '@/pages/ScheduleConfigPage'
import ProfilePage from '@/pages/Profile'
import SettingsPage from '@/pages/Settings'
import LoginPage from '@/pages/Login'
import RegisterPage from '@/pages/Register'
import AdminUsersPage from '@/pages/AdminUsers'
import AdminAuditLogsPage from '@/pages/AdminAuditLogs'

// Error Fallback component (uses hooks, must be inside Router)
function ErrorFallback() {
  const navigate = useNavigate()
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--color-canvas)',
      fontFamily: 'var(--font-body)',
    }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--color-ink)', marginBottom: 8 }}>
        Page load failed
      </div>
      <div style={{ fontSize: 14, color: 'var(--color-muted)', marginBottom: 24 }}>
        Please refresh the page or contact an administrator
      </div>
      <button
        onClick={() => navigate('/login')}
        style={{
          padding: '8px 16px',
          background: 'var(--color-primary)',
          color: 'var(--color-on-primary)',
          border: 'none',
          borderRadius: 6,
          cursor: 'pointer',
          fontSize: 14,
        }}
      >
        Back to Login
      </button>
    </div>
  )
}

// Error Boundary component
class ErrorBoundary extends React.Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: ReactNode; fallback?: ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.warn('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return <ErrorFallback />
    }
    return this.props.children
  }
}

// Protected route component - requires login
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f1f5f9'
      }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    // Redirect to login page, save current location to return after login
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

// Admin route - requires admin or super_admin role
function AdminRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f1f5f9'
      }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!user || (user.role !== 'admin' && user.role !== 'super_admin')) {
    return <Navigate to="/jobs" replace />
  }

  return <>{children}</>
}

// Public route - redirects authenticated users to home
function PublicRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f1f5f9'
      }}>
        <Spin size="large" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/jobs" replace />
  }

  return <>{children}</>
}

function ProtectedLayoutRoute() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <Outlet />
      </AppLayout>
    </ProtectedRoute>
  )
}

function AppRoutes() {
  const { theme: currentTheme } = useThemeContext()

  return (
    <>
      <ConfigProvider
        theme={{
          algorithm: currentTheme === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: currentTheme === 'dark' ? '#ffffff' : '#000000',
            colorBgLayout: currentTheme === 'dark' ? '#0a0a0a' : '#ffffff',
            colorBgContainer: currentTheme === 'dark' ? '#141414' : '#ffffff',
            colorText: currentTheme === 'dark' ? '#ffffff' : '#000000',
            colorTextSecondary: currentTheme === 'dark' ? '#888888' : '#666666',
            colorBorder: currentTheme === 'dark' ? '#2a2a2a' : '#e6e6e6',
            colorBorderSecondary: currentTheme === 'dark' ? '#333333' : '#d9d9d9',
            colorSuccess: '#1ea64a',
            colorWarning: '#f5a623',
            colorError: '#e5484d',
            colorInfo: '#3b82f6',
            borderRadius: 50,
            fontSize: 14,
            fontFamily: "'General Sans', 'DM Sans', system-ui, sans-serif",
            fontFamilyCode: "'JetBrains Mono', 'SF Mono', 'Menlo', monospace",
          },
          components: {
            Button: {
              borderRadius: 50,
              paddingInline: 20,
              controlHeight: 40,
            },
            Input: {
              borderRadius: 8,
              paddingInline: 14,
              controlHeight: 40,
            },
            Select: {
              borderRadius: 8,
              controlHeight: 40,
            },
            Table: {
              borderRadius: 24,
              headerBg: currentTheme === 'dark' ? '#141414' : '#f7f7f5',
            },
            Card: {
              borderRadius: 24,
            },
            Tag: {
              borderRadius: 50,
            },
            Menu: {
              itemSelectedBg: currentTheme === 'dark' ? '#ffffff' : '#000000',
              itemSelectedColor: currentTheme === 'dark' ? '#000000' : '#ffffff',
            },
          },
        }}
      >
        <AntdApp>
          <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <LoginPage />
                </PublicRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicRoute>
                  <RegisterPage />
                </PublicRoute>
              }
            />

            {/* Protected routes */}
            <Route element={<ProtectedLayoutRoute />}>
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/products" element={<ProductsPage />} />
              <Route path="/schedule" element={<ScheduleConfigPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route
                path="/admin/users"
                element={
                  <AdminRoute>
                    <AdminUsersPage />
                  </AdminRoute>
                }
              />
              <Route
                path="/admin/audit-logs"
                element={
                  <AdminRoute>
                    <AdminAuditLogsPage />
                  </AdminRoute>
                }
              />
            </Route>

            {/* Default routes */}
            <Route path="/" element={<Navigate to="/jobs" replace />} />
            <Route path="*" element={<Navigate to="/jobs" replace />} />
          </Routes>
        </BrowserRouter>
        </AntdApp>
      </ConfigProvider>
    </>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
