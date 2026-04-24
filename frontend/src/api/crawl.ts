import api from './client'
import type { CrawlLog } from '@/types'

export interface CrawlNowResponse {
  status: 'completed' | 'skipped' | 'error'
  total?: number
  success?: number
  errors?: number
  details?: unknown[]
  reason?: string
}

export const crawlApi = {
  crawlNow: () => api.post<CrawlNowResponse>('/crawl/crawl-now'),

  getLogs: (params?: {
    product_id?: number
    status?: string
    hours?: number
    limit?: number
  }) => api.get<CrawlLog[]>('/crawl/logs', { params }),
}
