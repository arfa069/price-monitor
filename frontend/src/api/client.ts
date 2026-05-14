import { notification } from 'antd'
import axios, { AxiosError } from 'axios'

type ErrorDetailItem = { msg?: string } | string
type ErrorResponse = { detail?: ErrorDetailItem[] | string }

const TOKEN_KEY = 'auth_token'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

// Request interceptor: add Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

const handleServerError = (status: number, msg: string) => {
  notification.error({
    message: `Server Error (${status})`,
    description: msg,
    duration: 6,
    placement: 'topRight',
  })
}

const handleTimeout = () => {
  notification.warning({
    message: 'Request Timeout',
    description: 'Server is responding slowly, please try again later',
    duration: 6,
    placement: 'topRight',
  })
}

const formatDetail = (detail: ErrorResponse['detail'], fallback: string) => {
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'string' ? item : item.msg || fallback))
      .join('; ')
  }
  return detail || fallback
}

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError<ErrorResponse>) => {
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = '/login'
      return Promise.reject(err)
    }
    if (err.response?.status && err.response.status >= 500) {
      handleServerError(err.response.status, err.message)
    } else if (err.response?.status && err.response.status >= 400) {
      err.message = formatDetail(
        err.response.data?.detail,
        `Request failed (${err.response.status})`,
      )
    } else if (err.code === 'ECONNABORTED' || !err.response) {
      handleTimeout()
    }
    return Promise.reject(err)
  },
)

export default api
