import api from './client'
import type { Alert, AlertCreateRequest, AlertUpdateRequest } from '@/types'

export const alertsApi = {
  list: (params?: { product_id?: number; active?: boolean }) =>
    api.get<Alert[]>('/alerts', { params }),

  get: (id: number) =>
    api.get<Alert>(`/alerts/${id}`),

  create: (data: AlertCreateRequest) =>
    api.post<Alert>('/alerts', data),

  update: (id: number, data: AlertUpdateRequest) =>
    api.patch<Alert>(`/alerts/${id}`, data),

  delete: (id: number) =>
    api.delete(`/alerts/${id}`),
}
