import api from './client'
import type {
  Job,
  JobCrawlResult,
  JobListResponse,
  JobSearchConfig,
  JobSearchConfigCreate,
  JobSearchConfigUpdate,
} from '@/types'

export const jobsApi = {
  getConfigs: (active?: boolean) =>
    api.get<JobSearchConfig[]>('/jobs/configs', {
      params: active !== undefined ? { active } : undefined,
    }),

  getConfig: (id: number) => api.get<JobSearchConfig>(`/jobs/configs/${id}`),

  createConfig: (data: JobSearchConfigCreate) =>
    api.post<JobSearchConfig>('/jobs/configs', data),

  updateConfig: (id: number, data: JobSearchConfigUpdate) =>
    api.patch<JobSearchConfig>(`/jobs/configs/${id}`, data),

  deleteConfig: (id: number) => api.delete(`/jobs/configs/${id}`),

  getJobs: (params?: {
    search_config_id?: number
    keyword?: string
    company?: string
    salary_min?: number
    salary_max?: number
    location?: string
    is_active?: boolean
    sort_by?: string
    sort_order?: string
    page?: number
    page_size?: number
  }) => api.get<JobListResponse>('/jobs', { params }),

  getJob: (jobId: string) => api.get<Job>(`/jobs/${jobId}`),

  crawlAll: () =>
    api.post<{ status: string; total: number; success: number; errors: number }>(
      '/jobs/crawl-now',
      undefined,
      { timeout: 600000 },  // 10分钟，长爬取任务
    ),

  crawlSingle: (configId: number) =>
    api.post<JobCrawlResult>(`/jobs/crawl-now/${configId}`, undefined, {
      timeout: 600000,
    }),
}
