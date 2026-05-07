import { useCallback, type ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { App, theme, Spin } from 'antd'
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
      <App
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: '#2563eb',
            colorBgLayout: '#f1f5f9',
            colorTextSecondary: '#64748b',
            borderRadius: 8,
            fontSize: 14,
          },
        }}
      >
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

            {/* 默认路由 */}
            <Route path="/" element={<Navigate to="/jobs" replace />} />
            <Route path="*" element={<Navigate to="/jobs" replace />} />
          </Routes>
        </BrowserRouter>
      </App>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
