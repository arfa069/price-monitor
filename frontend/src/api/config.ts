import api from './client'
import type { UserConfig } from '@/types'

export const configApi = {
  get: () => api.get<UserConfig>('/config'),

  update: (data: Partial<UserConfig>) => api.patch<UserConfig>('/config', data),

  getJobCrawlCron: () =>
    api.get<{ job_crawl_cron: string | null; default: string; timezone: string }>(
      '/config/job-crawl-cron',
    ),
  updateJobCrawlCron: (job_crawl_cron: string | null) =>
    api.put<{ job_crawl_cron: string | null }>('/config/job-crawl-cron', {
      job_crawl_cron,
    }),
}
