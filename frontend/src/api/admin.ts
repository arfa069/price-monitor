import api from './client'
import type { User } from '@/types'

export interface UserCreate {
  username: string
  email: string
  password: string
  role: string
}

export interface UserUpdate {
  username?: string
  email?: string
  role?: string
  is_active?: boolean
}

export interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
}

export const adminApi = {
  listUsers: async (params: {
    page?: number
    page_size?: number
    search?: string
    role?: string
  }): Promise<UserListResponse> => {
    const response = await api.get<UserListResponse>('/admin/users', { params })
    return response.data
  },

  createUser: async (data: UserCreate): Promise<User> => {
    const response = await api.post<User>('/admin/users', data)
    return response.data
  },

  updateUser: async (id: number, data: UserUpdate): Promise<User> => {
    const response = await api.patch<User>(`/admin/users/${id}`, data)
    return response.data
  },

  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/admin/users/${id}`)
  },
}
