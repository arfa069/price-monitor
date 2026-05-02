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
  job_crawl_cron: string | null
  created_at: string | null
  updated_at: string | null
}

export interface SchedulerJobStatus {
  registered: boolean
  cron_expression: string | null
  next_run_at: string | null
}

export interface SchedulerStatusResponse {
  scheduler: string
  timezone: string
  jobs: {
    product_crawl: SchedulerJobStatus
    product_platforms: Record<string, ProductPlatformCronSchedule>
    job_configs: Record<string, JobConfigScheduleInfo>
  }
}

export interface JobConfigCronUpdate {
  cron_expression: string | null
  cron_timezone?: string | null
}

export interface JobConfigScheduleInfo {
  cron_expression: string | null
  next_run_at: string | null
}

export interface ProductPlatformCron {
  id: number
  user_id: number
  platform: string
  cron_expression: string | null
  cron_timezone: string | null
  created_at: string
  updated_at: string
}

export interface ProductPlatformCronCreate {
  platform: string
  cron_expression?: string | null
  cron_timezone?: string | null
}

export interface ProductPlatformCronUpdate {
  cron_expression: string | null
  cron_timezone?: string | null
}

export interface ProductPlatformCronSchedule {
  cron_expression: string | null
  next_run_at: string | null
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

export interface JobSearchConfig {
  id: number
  user_id: number
  name: string
  keyword: string | null
  city_code: string | null
  salary_min: number | null
  salary_max: number | null
  experience: string | null
  education: string | null
  url: string
  active: boolean
  notify_on_new: boolean
  cron_expression: string | null
  cron_timezone: string | null
  created_at: string
  updated_at: string
}

export interface JobSearchConfigCreate {
  name: string
  keyword?: string
  city_code?: string
  salary_min?: number
  salary_max?: number
  experience?: string
  education?: string
  url: string
  active?: boolean
  notify_on_new?: boolean
  cron_expression?: string | null
  cron_timezone?: string | null
}

export interface JobSearchConfigUpdate {
  name?: string
  keyword?: string
  city_code?: string
  salary_min?: number
  salary_max?: number
  experience?: string
  education?: string
  url?: string
  active?: boolean
  notify_on_new?: boolean
  cron_expression?: string | null
  cron_timezone?: string | null
}

export interface Job {
  id: number
  job_id: string
  search_config_id: number
  title: string | null
  company: string | null
  company_id: string | null
  salary: string | null
  salary_min: number | null
  salary_max: number | null
  location: string | null
  experience: string | null
  education: string | null
  description: string | null
  url: string | null
  first_seen_at: string
  last_updated_at: string
  is_active: boolean
}

export interface JobListResponse {
  items: Job[]
  total: number
  page: number
  page_size: number
}

export interface JobCrawlResult {
  new_count: number
  updated_count: number
  deactivated_count: number
}
