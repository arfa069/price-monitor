import api from './client'
import type {
  ProductListResponse,
  Product,
  ProductCreateRequest,
  ProductUpdateRequest,
  BatchCreateItem,
  BatchOperationResult,
  PriceHistoryRecord,
} from '@/types'

export const productsApi = {
  list: (params: {
    platform?: string
    active?: boolean
    keyword?: string
    page?: number
    size?: number
  }) => api.get<ProductListResponse>('/products', { params }),

  get: (id: number) => api.get<Product>(`/products/${id}`),

  create: (data: ProductCreateRequest) => api.post<Product>('/products', data),

  update: (id: number, data: ProductUpdateRequest) =>
    api.patch<Product>(`/products/${id}`, data),

  delete: (id: number) => api.delete(`/products/${id}`),

  batchCreate: (items: BatchCreateItem[]) =>
    api.post<BatchOperationResult[]>('/products/batch-create', { items }),

  batchDelete: (ids: number[]) =>
    api.post<BatchOperationResult[]>('/products/batch-delete', { ids }),

  batchUpdate: (ids: number[], active?: boolean) =>
    api.post<BatchOperationResult[]>('/products/batch-update', { ids, active }),

  history: (id: number, days = 30, limit = 100) =>
    api.get<PriceHistoryRecord[]>(`/products/${id}/history`, {
      params: { days, limit },
    }),
}
