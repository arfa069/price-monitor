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
}

export interface ProductCreateRequest {
  platform: 'taobao' | 'jd' | 'amazon'
  url: string
  title?: string
  active?: boolean
}

export interface ProductUpdateRequest {
  platform?: 'taobao' | 'jd' | 'amazon'
  title?: string
  active?: boolean
  url?: string
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
  created_at: string | null
  updated_at: string | null
}

export interface PriceHistoryRecord {
  id: number
  product_id: number
  price: number
  scraped_at: string
}
