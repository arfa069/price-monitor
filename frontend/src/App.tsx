import { useCallback, type ReactNode } from 'react'
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { App as AntdApp, ConfigProvider, Spin, theme } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import AppLayout from '@/components/AppLayout'
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
      background: '#ffffff',
      fontFamily: 'system-ui, sans-serif',
    }}>
      <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
      <div style={{ fontSize: 18, fontWeight: 600, color: '#1f2937', marginBottom: 8 }}>
        页面加载失败
      </div>
      <div style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>
        请刷新页面或联系管理员
      </div>
      <button
        onClick={() => navigate('/login')}
        style={{
          padding: '8px 16px',
          background: '#2563eb',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          cursor: 'pointer',
          fontSize: 14,
        }}
      >
        返回登录页
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

// 受保护的路由组件 - 需要登录才能访问
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
    // 重定向到登录页，并记录当前位置以便登录后返回
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

// 管理员路由 - 需要 admin 或 super_admin 角色
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

// 公开路由 - 已登录用户访问时跳转到首页
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

function AppRoutes() {
  const queryClient = useQueryClient()

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries()
  }, [queryClient])

  return (
    <>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: '#000000',
            colorBgLayout: '#ffffff',
            colorBgContainer: '#ffffff',
            colorText: '#000000',
            colorTextSecondary: '#666666',
            colorBorder: '#bfbfbf',
            colorBorderSecondary: '#d9d9d9',
            borderRadius: 50,
            fontSize: 16,
            fontFamily: "'Inter', 'SF Pro Display', system-ui, -apple-system, sans-serif",
          },
          components: {
            Button: {
              borderRadius: 50,
              paddingInline: 20,
            },
            Input: {
              borderRadius: 8,
              paddingInline: 14,
            },
            Select: {
              borderRadius: 8,
            },
            Table: {
              borderRadius: 24,
            },
            Card: {
              borderRadius: 24,
            },
          },
        }}
      >
        <AntdApp>
          <BrowserRouter>
          <Routes>
            {/* 公开路由 */}
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

            {/* 受保护的路由 */}
            <Route
              path="/jobs"
              element={
                <ProtectedRoute>
                  <AppLayout onRefresh={handleRefresh}>
                    <JobsPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/products"
              element={
                <ProtectedRoute>
                  <AppLayout onRefresh={handleRefresh}>
                    <ProductsPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/schedule"
              element={
                <ProtectedRoute>
                  <AppLayout onRefresh={handleRefresh}>
                    <ScheduleConfigPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <AppLayout onRefresh={handleRefresh}>
                    <ProfilePage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <AppLayout onRefresh={handleRefresh}>
                    <SettingsPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <AdminRoute>
                  <AppLayout onRefresh={handleRefresh}>
                    <AdminUsersPage />
                  </AppLayout>
                </AdminRoute>
              }
            />
            <Route
              path="/admin/audit-logs"
              element={
                <AdminRoute>
                  <AppLayout onRefresh={handleRefresh}>
                    <AdminAuditLogsPage />
                  </AppLayout>
                </AdminRoute>
              }
            />

            {/* 默认路由 */}
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
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ErrorBoundary>
  )
}
