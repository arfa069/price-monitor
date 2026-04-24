import api from './client'

export interface CrawlNowResponse {
  status: 'completed' | 'skipped' | 'error'
  total?: number
  success?: number
  errors?: number
  details?: unknown[]
  reason?: string
}

export interface CrawlLog {
  id: number
  product_id: number | null
  platform: string
  status: string
  price: number | null
  currency: string | null
  timestamp: string
  error_message: string | null
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
