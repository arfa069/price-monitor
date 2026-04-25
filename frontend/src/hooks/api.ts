import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productsApi } from '@/api/products'
import { configApi } from '@/api/config'
import { crawlApi } from '@/api/crawl'
import { alertsApi } from '@/api/alerts'
import type { AlertUpdateRequest, CrawlLog } from '@/types'

export const useProducts = (params: {
  platform?: string
  active?: boolean
  keyword?: string
  page?: number
  size?: number
}) => {
  const { platform, active, keyword, page, size } = params
  return useQuery({
    queryKey: ['products', platform ?? '', active ?? '', keyword ?? '', page ?? 1, size ?? 15],
    queryFn: () => productsApi.list(params).then((res) => res.data),
    staleTime: 10_000,
  })
}

export const useCreateProduct = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: productsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}

export const useUpdateProduct = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      productsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}

export const useDeleteProduct = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: productsApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}

export const useBatchCreate = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: productsApi.batchCreate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}

export const useBatchDelete = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: productsApi.batchDelete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}

export const useBatchUpdate = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ids, active }: { ids: number[]; active?: boolean }) =>
      productsApi.batchUpdate(ids, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}

export const useConfig = () => {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => configApi.get().then((res) => res.data),
  })
}

export const useUpdateConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: configApi.update,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config'] }),
  })
}

export const useProductHistory = (id: number, days = 30) => {
  return useQuery({
    queryKey: ['product-history', id, days],
    queryFn: () => productsApi.history(id, days).then((res) => res.data),
    enabled: !!id,
  })
}

export const useCrawlNow = () => {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const response = await crawlApi.crawlNow()
      const data = response.data

      if (data.status === 'skipped') {
        return { type: 'skipped', reason: data.reason }
      }

      if (data.status === 'error') {
        return { type: 'error', reason: data.reason }
      }

      // Poll for result
      const taskId = data.task_id!
      const maxAttempts = 60 // 60 * 3s = 3 minutes max
      let attempts = 0

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 3000))
        attempts++

        try {
          const statusRes = await crawlApi.getStatus(taskId)
          const status = statusRes.data

          if (status.status === 'completed') {
            // Get full result
            const resultRes = await crawlApi.getResult(taskId)
            const result = resultRes.data
            qc.invalidateQueries({ queryKey: ['crawl-logs'] })
            return {
              type: 'completed',
              total: result.total,
              success: result.success,
              errors: result.errors,
              details: result.details,
            }
          }

          if (status.status === 'failed') {
            return { type: 'error', reason: status.reason }
          }
          // pending or running - continue polling
        } catch (e) {
          // Network error during polling - continue
          console.warn('Polling error:', e)
        }
      }

      return { type: 'error', reason: 'timeout_polling' }
    },
  })
}

export const useAlerts = (productId?: number) => {
  return useQuery({
    queryKey: ['alerts', productId],
    queryFn: () => alertsApi.list(productId !== undefined ? { product_id: productId } : undefined).then((res) => res.data),
    enabled: productId !== undefined,
  })
}

export const useAllAlerts = () => {
  return useQuery({
    queryKey: ['alerts', 'all'],
    queryFn: () => alertsApi.list().then((res) => res.data),
  })
}

export const useCreateAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: alertsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export const useUpdateAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlertUpdateRequest }) =>
      alertsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export const useDeleteAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: alertsApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export const useCrawlLogs = (params?: { product_id?: number; hours?: number; limit?: number }) => {
  return useQuery<CrawlLog[]>({
    queryKey: ['crawl-logs', params],
    queryFn: () => crawlApi.getLogs(params).then((res) => res.data),
    refetchInterval: 60000, // 每分钟自动刷新
  })
}
