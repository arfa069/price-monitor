import api from './client'
import type { UserConfig } from '@/types'

export const configApi = {
  get: () => api.get<UserConfig>('/config'),

  update: (data: Partial<UserConfig>) => api.patch<UserConfig>('/config', data),
}
