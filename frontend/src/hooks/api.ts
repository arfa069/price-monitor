import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { alertsApi } from '@/api/alerts'
import { configApi } from '@/api/config'
import { crawlApi } from '@/api/crawl'
import { jobsApi } from '@/api/jobs'
import { productsApi } from '@/api/products'
import type { AlertUpdateRequest, CrawlLog, JobSearchConfigUpdate } from '@/types'

export type CrawlNowMutationResult =
  | { type: 'skipped'; reason?: string }
  | { type: 'error'; reason?: string }
  | {
      type: 'completed'
      total: number
      success: number
      errors: number
      details: unknown[]
    }

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
    mutationFn: ({
      id,
      data,
    }: {
      id: number
      data: Parameters<typeof productsApi.update>[1]
    }) => productsApi.update(id, data),
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
    mutationFn: async (): Promise<CrawlNowMutationResult> => {
      const response = await crawlApi.crawlNow()
      const data = response.data

      if (data.status === 'skipped') return { type: 'skipped', reason: data.reason }
      if (data.status === 'error') return { type: 'error', reason: data.reason }

      const taskId = data.task_id!
      let attempts = 0
      const maxAttempts = 60

      while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 3000))
        attempts += 1
        try {
          const statusRes = await crawlApi.getStatus(taskId)
          const status = statusRes.data
          if (status.status === 'completed') {
            const resultRes = await crawlApi.getResult(taskId)
            const result = resultRes.data
            qc.invalidateQueries({ queryKey: ['crawl-logs'] })
            return {
              type: 'completed',
              total: result.total ?? 0,
              success: result.success ?? 0,
              errors: result.errors ?? 0,
              details: result.details ?? [],
            }
          }
          if (status.status === 'failed') {
            return { type: 'error', reason: status.reason }
          }
        } catch (e) {
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
    queryFn: () =>
      alertsApi
        .list(productId !== undefined ? { product_id: productId } : undefined)
        .then((res) => res.data),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}

export const useUpdateAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlertUpdateRequest }) =>
      alertsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}

export const useDeleteAlert = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: alertsApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })
}

export const useCrawlLogs = (params?: { product_id?: number; hours?: number; limit?: number }) => {
  return useQuery<CrawlLog[]>({
    queryKey: ['crawl-logs', params],
    queryFn: () => crawlApi.getLogs(params).then((res) => res.data),
    refetchInterval: 60_000,
  })
}

export const useJobConfigs = (active?: boolean) => {
  return useQuery({
    queryKey: ['job-configs', active],
    queryFn: () => jobsApi.getConfigs(active).then((res) => res.data),
  })
}

export const useJobConfig = (id: number) => {
  return useQuery({
    queryKey: ['job-config', id],
    queryFn: () => jobsApi.getConfig(id).then((res) => res.data),
    enabled: !!id,
  })
}

export const useCreateJobConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.createConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-configs'] }),
  })
}

export const useUpdateJobConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: JobSearchConfigUpdate }) =>
      jobsApi.updateConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-configs'] }),
  })
}

export const useDeleteJobConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.deleteConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['job-configs'] }),
  })
}

export const useJobs = (params?: {
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
}) => {
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: () => jobsApi.getJobs(params).then((res) => res.data),
    staleTime: 30_000,
  })
}

export const useJob = (jobId: string) => {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.getJob(jobId).then((res) => res.data),
    enabled: !!jobId,
  })
}

export const useCrawlAllJobs = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.crawlAll,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['job-configs'] })
    },
  })
}

export const useCrawlSingleJob = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.crawlSingle,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['job-configs'] })
    },
  })
}
