import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productsApi } from '@/api/products'
import { configApi } from '@/api/config'
import { crawlApi } from '@/api/crawl'
import { alertsApi } from '@/api/alerts'
import type { AlertUpdateRequest } from '@/types'

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
  return useMutation({
    mutationFn: () => crawlApi.crawlNow().then((res) => res.data),
  })
}

export const useAlerts = (productId?: number) => {
  return useQuery({
    queryKey: ['alerts', productId],
    queryFn: () => alertsApi.list(productId !== undefined ? { product_id: productId } : undefined).then((res) => res.data),
    enabled: productId !== undefined,
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
