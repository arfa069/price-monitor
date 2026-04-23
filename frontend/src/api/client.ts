import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status >= 500) {
      console.error('服务器错误:', err.response.status, err.message)
    } else if (err.response?.status >= 400) {
      // Format 4xx validation errors for caller
      const detail = err.response?.data?.detail
      err.message = Array.isArray(detail)
        ? detail.map((d: any) => d.msg || d).join('; ')
        : (detail || `请求失败 (${err.response.status})`)
    } else if (err.code === 'ECONNABORTED' || !err.response) {
      console.error('请求超时或网络错误')
    }
    return Promise.reject(err)
  },
)

export default api
