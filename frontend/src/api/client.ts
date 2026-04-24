import { notification } from 'antd'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
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
    description: '服务器响应太慢，请稍后重试',
    duration: 6,
    placement: 'topRight',
  })
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status >= 500) {
      handleServerError(err.response.status, err.message)
    } else if (err.response?.status >= 400) {
      const detail = err.response?.data?.detail
      err.message = Array.isArray(detail)
        ? detail.map((d: any) => d.msg || d).join('; ')
        : (detail || `请求失败 (${err.response.status})`)
    } else if (err.code === 'ECONNABORTED' || !err.response) {
      handleTimeout()
    }
    return Promise.reject(err)
  },
)

export default api
