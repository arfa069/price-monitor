import api from './client'

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

export interface User {
  id: number
  username: string
  email: string
  created_at?: string
}

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<AuthResponse>('/auth/login', data),

  register: (data: RegisterRequest) =>
    api.post<AuthResponse>('/auth/register', data),

  getMe: () =>
    api.get<User>('/auth/me'),
}
