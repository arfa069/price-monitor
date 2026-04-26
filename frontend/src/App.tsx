import { useCallback } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import AppLayout from '@/components/AppLayout'
import JobsPage from '@/pages/JobsPage'
import ProductsPage from '@/pages/ProductsPage'
import ScheduleConfigPage from '@/pages/ScheduleConfigPage'

export default function App() {
  const queryClient = useQueryClient()

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries()
  }, [queryClient])

  return (
    <ConfigProvider
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
        <AppLayout onRefresh={handleRefresh}>
          <Routes>
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/schedule" element={<ScheduleConfigPage />} />
            <Route path="/" element={<Navigate to="/jobs" replace />} />
            <Route path="*" element={<Navigate to="/jobs" replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </ConfigProvider>
  )
}
