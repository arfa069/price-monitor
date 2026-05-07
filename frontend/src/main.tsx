import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

type QueryError = {
  response?: { status?: number }
  code?: string
  message?: string
}

const queryCache = new QueryCache({
  onError: (error) => {
    const err = error as QueryError
    if (err.response?.status != null && err.response.status >= 500) {
      return
    }
    if (err.code === 'ECONNABORTED' || !err.response) {
      return
    }
    if (err.response?.status != null && err.response.status >= 400) {
      console.error(`请求失败: ${err.message || '未知错误'}`)
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
