export interface User {
  id: number
  username: string
  email: string
  role: string
  is_active?: boolean
  created_at?: string
}

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
  data_retention_days: number
  created_at: string | null
  updated_at: string | null
}

export interface SchedulerJobStatus {
  registered: boolean
  cron_expression: string | null
  next_run_at: string | null
}

export interface ProductPlatformCronSchedule {
  cron_expression: string | null
  next_run_at: string | null
}

export interface JobConfigScheduleInfo {
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
  deactivation_threshold: number
  cron_expression: string | null
  cron_timezone: string | null
  enable_match_analysis: boolean
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
  deactivation_threshold?: number
  cron_expression?: string | null
  cron_timezone?: string | null
  enable_match_analysis?: boolean
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
  deactivation_threshold?: number
  cron_expression?: string | null
  cron_timezone?: string | null
  enable_match_analysis?: boolean
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

export interface UserResume {
  id: number
  user_id: number
  name: string
  resume_text: string
  created_at: string
  updated_at: string
}

export interface UserResumeCreateRequest {
  name: string
  resume_text: string
}

export interface UserResumeUpdateRequest {
  name?: string
  resume_text?: string
}

export interface MatchResultWithJob {
  id: number
  user_id: number
  resume_id: number
  job_id: number
  match_score: number
  match_reason: string | null
  apply_recommendation: string | null
  llm_model_used: string | null
  created_at: string
  updated_at: string
  job_title: string | null
  job_company: string | null
  job_salary: string | null
  job_location: string | null
  job_url: string | null
  job_description: string | null
}

export interface MatchResultListResponse {
  items: MatchResultWithJob[]
  total: number
  page: number
  page_size: number
}

export interface MatchAnalyzeRequest {
  resume_id: number
  job_ids?: number[] | null
}

export interface MatchAnalyzeResponse {
  processed: number
  created: number
  updated: number
  skipped: number
  items: MatchResultWithJob[]
}
