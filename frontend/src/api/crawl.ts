import api from './client'
import type { CrawlLog } from '@/types'

export interface CrawlNowResponse {
  status: 'pending' | 'skipped' | 'error'
  task_id?: string
  message?: string
  reason?: string
}

export interface CrawlStatusResponse {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  total: number
  success: number
  errors: number
  reason?: string
}

export interface CrawlResultResponse {
  status: 'completed' | 'pending' | 'running' | 'error'
  task_id: string
  total?: number
  success?: number
  errors?: number
  details?: unknown[]
  reason?: string
}

export const crawlApi = {
  crawlNow: () => api.post<CrawlNowResponse>('/crawl/crawl-now'),

  getStatus: (taskId: string) => api.get<CrawlStatusResponse>(`/crawl/status/${taskId}`),

  getResult: (taskId: string) => api.get<CrawlResultResponse>(`/crawl/result/${taskId}`),

  getLogs: (params?: {
    product_id?: number
    status?: string
    hours?: number
    limit?: number
  }) => api.get<CrawlLog[]>('/crawl/logs', { params }),
}
