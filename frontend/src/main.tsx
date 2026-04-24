import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, QueryCache } from '@tanstack/react-query'
import { message } from 'antd'
import App from './App'

const queryCache = new QueryCache({
  onError: (error) => {
    const err = error as { response?: { status?: number }; code?: string }
    if (err.response?.status != null && err.response.status >= 500) {
      // Handled by axios interceptor (client.ts)
    } else if (err.code === 'ECONNABORTED' || !err.response) {
      // Handled by axios interceptor (client.ts)
    } else if (err.response?.status != null && err.response.status >= 400) {
      message.error('请求失败：' + (err as any).message)
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
