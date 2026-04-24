export interface Product {
  id: number
  user_id: number
  platform: string
  url: string
  title: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export interface ProductListResponse {
  items: Product[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface ProductCreateRequest {
  platform: 'taobao' | 'jd' | 'amazon'
  url: string
  title?: string
  active?: boolean
}

export interface ProductUpdateRequest {
  title?: string
  active?: boolean
  url?: string
}

export interface ProductFormValues {
  platform?: 'taobao' | 'jd' | 'amazon'
  url: string
  title?: string
  active?: boolean
}

export interface BatchImportRow {
  url: string
  platform: string
  title?: string
}

export interface BatchCreateItem {
  url: string
  platform: 'taobao' | 'jd' | 'amazon'
  title?: string
}

export interface BatchOperationResult {
  id: number | null
  url: string | null
  success: boolean
  error: string | null
}

export interface UserConfig {
  id: number
  username: string
  feishu_webhook_url: string
  crawl_frequency_hours: number
  data_retention_days: number
  crawl_cron: string | null
  crawl_timezone: string | null
  created_at: string | null
  updated_at: string | null
}

export interface PriceHistoryRecord {
  id: number
  product_id: number
  price: number
  scraped_at: string
}

export interface Alert {
  id: number
  product_id: number
  alert_type: string
  threshold_percent: number | null
  last_notified_at: string | null
  last_notified_price: number | null
  active: boolean
  created_at: string
  updated_at: string
}

export interface AlertCreateRequest {
  product_id: number
  threshold_percent?: number
  active?: boolean
}

export interface AlertUpdateRequest {
  threshold_percent?: number
  active?: boolean
}

export interface CrawlLog {
  id: number
  product_id: number | null
  platform: string | null
  status: string | null
  price: number | null
  currency: string | null
  timestamp: string
  error_message: string | null
}
