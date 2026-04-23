import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, QueryCache } from '@tanstack/react-query'
import { message } from 'antd'
import App from './App'

const queryCache = new QueryCache({
  onError: (error) => {
    const err = error as { response?: { status?: number }; code?: string }
    if (err.response?.status != null && err.response.status >= 500) {
      message.error('服务器错误，请稍后重试')
    } else if (err.code === 'ECONNABORTED' || !err.response) {
      message.error('请求超时或网络错误，请检查网络连接')
    }
  },
})

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
  queryCache,
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
