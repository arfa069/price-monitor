import api from './client'
import type {
  Job,
  JobConfigCronUpdate,
  JobConfigScheduleInfo,
  JobListResponse,
  JobSearchConfig,
  JobSearchConfigCreate,
  JobSearchConfigUpdate,
} from '@/types'

export interface JobCrawlStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  total: number
  success: number
  errors: number
}

export interface JobCrawlFinalResult {
  status: string
  task_id: string
  total: number
  success: number
  errors: number
  reason?: string
}

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

  updateConfigCron: (id: number, data: JobConfigCronUpdate) =>
    api.patch<JobSearchConfig>(`/jobs/configs/${id}/cron`, data),

  getJobConfigSchedules: () =>
    api.get<{ configs: (JobConfigScheduleInfo & { config_id: number })[] }>(
      '/jobs/scheduler/job-configs',
    ),

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
    api.post<{ status: string; task_id: string; message: string }>(
      '/jobs/crawl-now',
      undefined,
      { timeout: 10000 },
    ),

  crawlSingle: (configId: number) =>
    api.post<{ status: string; task_id: string; message: string }>(
      `/jobs/crawl-now/${configId}`,
      undefined,
      { timeout: 10000 },
    ),

  getCrawlStatus: (taskId: string) =>
    api.get<JobCrawlStatus>(`/jobs/crawl/status/${taskId}`),

  getCrawlResult: (taskId: string) =>
    api.get<JobCrawlFinalResult>(`/jobs/crawl/result/${taskId}`),
}
