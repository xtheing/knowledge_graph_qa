import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API接口定义
export const paperAPI = {
  // 上传论文
  upload: (file, paperId = null, maxChunks = 50) => {
    const formData = new FormData()
    formData.append('file', file)
    if (paperId) formData.append('paper_id', paperId)
    formData.append('max_chunks', maxChunks)
    
    return api.post('/papers/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  
  // 删除论文
  delete: (paperId) => api.delete(`/papers/${paperId}`),
  
  // 获取论文实体
  getEntities: (paperId, limit = 100) => 
    api.get(`/papers/${paperId}/entities?limit=${limit}`),
}

export const entityAPI = {
  // 搜索实体
  search: (keyword, paperId = null, entityType = null, limit = 20) => 
    api.post('/entities/search', { keyword, paper_id: paperId, entity_type: entityType, limit }),
  
  // 获取实体邻居
  getNeighbors: (entityName, paperId = null, depth = 1) => 
    api.get(`/entities/${encodeURIComponent(entityName)}/neighbors?paper_id=${paperId}&depth=${depth}`),
}

export const qaAPI = {
  // 问答
  ask: (question, paperId = null, includeContext = false) => 
    api.post('/ask', { question, paper_id: paperId, include_context: includeContext }),
}

export const statsAPI = {
  // 获取统计信息
  getStats: () => api.get('/stats'),
  
  // 健康检查
  healthCheck: () => api.get('/health'),
}

export default api