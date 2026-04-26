import { notification } from 'antd'
import axios, { AxiosError } from 'axios'

type ErrorDetailItem = { msg?: string } | string
type ErrorResponse = { detail?: ErrorDetailItem[] | string }

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

const handleServerError = (status: number, msg: string) => {
  notification.error({
    message: `服务器错误 (${status})`,
    description: msg,
    duration: 6,
    placement: 'topRight',
  })
}

const handleTimeout = () => {
  notification.warning({
    message: '请求超时',
    description: '服务器响应过慢，请稍后重试',
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
    if (err.response?.status && err.response.status >= 500) {
      handleServerError(err.response.status, err.message)
    } else if (err.response?.status && err.response.status >= 400) {
      err.message = formatDetail(
        err.response.data?.detail,
        `请求失败 (${err.response.status})`,
      )
    } else if (err.code === 'ECONNABORTED' || !err.response) {
      handleTimeout()
    }
    return Promise.reject(err)
  },
)

export default api
