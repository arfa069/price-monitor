import { useCallback } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import AppLayout from '@/components/AppLayout'
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
          colorPrimary: '#1677ff',
          borderRadius: 6,
          fontSize: 14,
        },
      }}
    >
      <BrowserRouter>
        <AppLayout onRefresh={handleRefresh}>
          <Routes>
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/schedule" element={<ScheduleConfigPage />} />
            <Route path="/" element={<Navigate to="/products" replace />} />
            <Route path="*" element={<Navigate to="/products" replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </ConfigProvider>
  )
}
