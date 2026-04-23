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
    } else if (err.code === 'ECONNABORTED' || !err.response) {
      console.error('请求超时或网络错误')
    }
    return Promise.reject(err)
  },
)

export default api
