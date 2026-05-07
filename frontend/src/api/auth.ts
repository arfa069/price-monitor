import api from './client'
import type { User } from '@/types'

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  password_confirm: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
}

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<AuthResponse>('/auth/login', data),

  register: (data: RegisterRequest) =>
    api.post<AuthResponse>('/auth/register', data),

  getMe: () =>
    api.get<User>('/auth/me'),

  updateProfile: async (data: { username?: string; email?: string }) => {
    const response = await api.patch<User>('/auth/me', data)
    return response
  },

  changePassword: async (data: { old_password: string; new_password: string }) => {
    const response = await api.post('/auth/me/password', data)
    return response
  },

  updateConfig: async (data: { feishu_webhook_url?: string; data_retention_days?: number }) => {
    const response = await api.patch('/auth/me/config', data)
    return response
  },
}
