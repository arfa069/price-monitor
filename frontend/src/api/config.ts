import api from './client'
import type { SchedulerStatusResponse, UserConfig } from '@/types'

export const configApi = {
  get: () => api.get<UserConfig>('/config'),

  update: (data: Partial<UserConfig>) => api.patch<UserConfig>('/config', data),

  getSchedulerStatus: () =>
    api.get<SchedulerStatusResponse>('/scheduler/status'),
}
