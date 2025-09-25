import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',  // 基础URL，所有请求都会加上这个前缀
  timeout: 60000,   // 增加超时时间到60秒
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add request interceptor for error handling
api.interceptors.request.use(
  config => {
    // 如果是上传文件，移除Content-Type让浏览器自动设置
    if (config.url?.includes('/upload') && config.method === 'post') {
      delete config.headers['Content-Type']
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    ElMessage.error('请求发送失败')
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
api.interceptors.response.use(
  response => {
    return response
  },
  error => {
    console.error('API Error:', error.response?.data || error.message)
    
    // 处理不同的错误情况
    if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请重试')
    } else if (error.response) {
      switch (error.response.status) {
        case 400:
          ElMessage.error(error.response.data?.detail || '请求参数错误')
          break
        case 401:
          ElMessage.error('未授权，请重新登录')
          break
        case 403:
          ElMessage.error('没有权限执行此操作')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 413:
          ElMessage.error('上传的文件太大')
          break
        case 415:
          ElMessage.error('不支持的文件类型')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error('请求失败，请重试')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

// File loading API
export const loadingApi = {
  // Get all files
  getFiles: () => {
    return api.get('/loading/files')
  },

  // Get all raw uploaded files (from uploads directory)
  getUploadedFiles: () => {
    console.log('API: Fetching uploaded files')
    return api.get('/loading/uploads')
      .then(response => {
        console.log('API: Uploaded files response:', response.data)
        // 检查响应结构
        if (!response.data) {
          console.warn('API: Empty uploaded files response data')
          response.data = { files: [] }
        } else if (!response.data.files && Array.isArray(response.data)) {
          console.warn('API: Response is array but missing files property, wrapping in files property')
          response.data = { files: response.data }
        } else if (!response.data.files) {
          console.warn('API: Response missing files property')
          response.data = { files: [] }
        }
        return response
      })
      .catch(error => {
        console.error('API: Error fetching uploaded files:', error)
        throw error
      })
  },

  // Get details for a specific file
  getFileDetails: (fileId) => {
    return api.get(`/loading/files/${fileId}`)
  },

  // Delete a file
  deleteFile: (fileId) => {
    return api.delete(`/loading/files/${fileId}`, {
      params: { delete_files: true }
    })
  },
  
  // Get available document loaders
  getAvailableLoaders: () => {
    return api.get('/loading/available-loaders')
  },
  
  // Preview a document (with page support for PDFs)
  getFilePreview: (fileId, page = 1) => {
    return api.get(`/loading/files/${fileId}/preview`, { params: { page } })
  },
  
  // Upload a file
  uploadFile: (formData) => {
    return api.post('/loading/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // Load a document with the specified loader
  loadDocument: (fileId, loaderType, additionalParams = {}) => {
    return api.post('/loading/load', {
      file_id: fileId,
      loader_type: loaderType,
      additional_params: additionalParams
    })
  },

  // Download the original file
  downloadFile: (fileId) => {
    window.open(`/api/loading/files/${fileId}/download`, '_blank')
    return Promise.resolve({ success: true })
  }
}

// 文档分块API
export const chunkingApi = {
  // 获取分块策略列表
  getChunkingStrategies: () => {
    console.log('API: Fetching chunking strategies')
    return api.get('/chunking/strategies')
      .then(response => {
        console.log('API: Chunking strategies response:', response.data)
        return response
      })
      .catch(error => {
        console.error('API: Error fetching chunking strategies:', error)
        // 返回一个默认的策略列表，避免UI崩溃
        if (error.response && error.response.status === 404) {
          console.warn('API: Returning default strategies due to 404')
          return {
            data: [
              {
                "id": "fixed_size",
                "name": "固定大小",
                "description": "将文本按固定大小分块，并可设置重叠部分",
                "parameters": [
                  {"name": "chunk_size", "type": "number", "default": 1000, "min": 100, "max": 10000, "description": "每个块的大小（字符数）"},
                  {"name": "chunk_overlap", "type": "number", "default": 200, "min": 0, "max": 5000, "description": "块之间重叠的字符数"}
                ]
              }
            ]
          }
        }
        throw error
      })
  },
  
  // 获取文档分块
  getDocumentChunks: (fileId) => {
    console.log('API: Fetching chunks for file:', fileId)
    return api.get(`/chunking/documents/${fileId}/chunks`)
      .then(response => {
        console.log('API: Chunks response data:', response.data)
        // 检查响应结构
        if (!response.data) {
          console.warn('API: Empty response data, creating default structure')
          response.data = { chunks: [] }
        } else if (!response.data.chunks && !Array.isArray(response.data)) {
          console.warn('API: Response missing chunks property and is not an array, creating default structure')
          response.data = { chunks: [] }
        } else if (Array.isArray(response.data)) {
          console.log('API: Response is an array, wrapping in chunks property')
          response.data = { chunks: response.data }
        }
        return response
      })
      .catch(error => {
        console.error('API: Error fetching chunks:', error)
        if (error.response && error.response.status === 404) {
          console.warn('API: Returning empty chunks due to 404')
          return { data: { chunks: [] } }
        }
        throw error
      })
  },
  
  // 获取分块数据的JSON文件
  getChunksJson: (fileId) => {
    console.log('API: Fetching JSON for file:', fileId)
    return api.get(`/chunking/documents/${fileId}/chunks/json`)
      .then(response => {
        console.log('API: JSON response data:', response.data)
        // 检查响应结构
        if (!response.data) {
          console.warn('API: Empty JSON response data, creating default structure')
          response.data = { chunks: [] }
        } else if (!response.data.chunks && !Array.isArray(response.data)) {
          console.warn('API: JSON response missing chunks property and is not an array, creating default structure')
          response.data = { chunks: [] }
        } else if (Array.isArray(response.data)) {
          console.log('API: JSON response is an array, wrapping in chunks property')
          response.data = { chunks: response.data }
        }
        return response
      })
      .catch(error => {
        console.error('API: Error fetching JSON:', error)
        if (error.response && error.response.status === 404) {
          console.warn('API: Returning empty JSON due to 404')
          return { data: { chunks: [] } }
        }
        throw error
      })
  },
  
  // 对文档进行分块
  chunkDocument: (fileId, strategy = 'fixed_size', params = {}) => {
    console.log('API: Chunking document:', { fileId, strategy, params })
    return api.post(`/chunking/documents/${fileId}/chunk`, {
      strategy,
      params
    })
      .then(response => {
        console.log('API: Chunk response data:', response.data)
        // 检查响应结构
        if (!response.data) {
          console.warn('API: Empty chunk response data, creating default structure')
          response.data = { chunks: [] }
        } else if (!response.data.chunks && !Array.isArray(response.data)) {
          console.warn('API: Chunk response missing chunks property and is not an array, creating default structure')
          response.data = { chunks: [] }
        } else if (Array.isArray(response.data)) {
          console.log('API: Chunk response is an array, wrapping in chunks property')
          response.data = { chunks: response.data }
        }
        return response
      })
      .catch(error => {
        console.error('API: Error chunking document:', error)
        throw error
      })
  },
  
  // 删除文档分块
  deleteChunks: (fileId) => {
    console.log('API: Deleting chunks for file:', fileId)
    return api.delete(`/chunking/documents/${fileId}/chunks`)
      .then(response => {
        console.log('API: Delete response data:', response.data)
        return response
      })
      .catch(error => {
        console.error('API: Error deleting chunks:', error)
        throw error
      })
  },
  
  // 检查文档是否已分块
  hasChunks: async (fileId) => {
    console.log('API: Checking chunks for file:', fileId)
    try {
      const response = await api.get(`/chunking/documents/${fileId}/chunks`)
      console.log('API: Check response status:', response.status)
      if (response.data && response.data.chunks && response.data.chunks.length > 0) {
        console.log('API: Document has chunks:', response.data.chunks.length)
        return true
      } else if (Array.isArray(response.data) && response.data.length > 0) {
        console.log('API: Document has chunks (array):', response.data.length)
        return true
      }
      console.log('API: Document has no chunks')
      return false
    } catch (error) {
      if (error.response && error.response.status === 404) {
        console.log('API: No chunks found (404)')
        return false
      }
      console.error('API: Error checking chunks:', error)
      throw error
    }
  }
}

// Document parsing API
export const parsingApi = {
  // 解析文档
  parseDocument: (fileId, parseMethod = 'full_text', includeTables = false) => {
    const formData = new FormData()
    formData.append('file_id', fileId)
    formData.append('parse_method', parseMethod)
    formData.append('include_tables', includeTables)
    
    return api.post('/parsing/parse', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 获取解析结果
  getParsingResult: (parsingId) => {
    return api.get(`/parsing/parse/${parsingId}`)
  },

  // 获取文件支持的解析方法
  getAvailableMethods: (fileId) => {
    return api.get(`/parsing/parse/${fileId}/methods`)
  },

  // 获取文件的解析历史
  getParsingHistory: (fileId) => {
    return api.get(`/parsing/parse/history/${fileId}`)
  },

  // 下载解析结果
  downloadParsingResult: (parsingId, format = 'json') => {
    window.open(`/api/parsing/parse/${parsingId}/download?format=${format}`, '_blank')
    return Promise.resolve({ success: true })
  }
}

// 向量嵌入API
export const embeddingApi = {
  // 获取可用的嵌入提供商
  getEmbeddingProviders: () => {
    return api.get('/embedding/providers')
  },
  
  // 获取特定提供商的模型
  getProviderModels: (providerId) => {
    return api.get(`/embedding/providers/${providerId}/models`)
  },
  
  // 获取JSON目录下的所有文件
  getJsonFiles: () => {
    return api.get('/embedding/json-files')
  },
  
  // 为文档创建嵌入
  createEmbeddings: (fileId, providerId, modelId, options = {}) => {
    return api.post('/embedding/create', {
      file_id: fileId,
      provider_id: providerId,
      model_id: modelId,
      options
    })
  },
  
  // 获取文档的嵌入历史
  getEmbeddingHistory: (fileId) => {
    return api.get(`/embedding/history/${fileId}`)
  },
  
  // 获取嵌入详情
  getEmbeddingDetails: (embeddingId) => {
    return api.get(`/embedding/${embeddingId}`)
  },
  
  // 下载嵌入结果
  downloadEmbedding: (embeddingId, format = 'json') => {
    window.open(`/api/embedding/${embeddingId}/download?format=${format}`, '_blank')
    return Promise.resolve({ success: true })
  },
  
  // 获取嵌入可视化数据
  getEmbeddingVisualization: (embeddingId, method = 'tsne', dimensions = 2) => {
    return api.get(`/embedding/${embeddingId}/visualize`, {
      params: {
        method,
        dimensions
      }
    })
  }
}

// 向量索引API
export const indexingApi = {
  // 获取可用的向量数据库
  getVectorDatabases: () => {
    return api.get('/indexing/databases')
  },
  
  // 创建索引
  createIndex: (embeddingId, dbType, indexName, config = {}) => {
    return api.post('/indexing/create', {
      embedding_id: embeddingId,
      db_type: dbType,
      index_name: indexName,
      config
    })
  },
  
  // 获取索引列表
  getIndices: () => {
    return api.get('/indexing/indices')
  },
  
  // 删除索引
  deleteIndex: (indexId) => {
    return api.delete(`/indexing/indices/${indexId}`)
  },
  
  // 搜索向量数据
  searchIndex: (indexId, query, topK = 5, filter = {}) => {
    return api.post(`/indexing/indices/${indexId}/search`, {
      query,
      top_k: topK,
      filter
    })
  },
  
  // 保存搜索结果
  saveSearchResult: (searchId) => {
    return api.post(`/indexing/search/${searchId}/save`)
  },
  
  // 获取搜索历史
  getSearchHistory: () => {
    return api.get('/indexing/search/history')
  }
}

// 文本生成API
export const generationApi = {
  // 获取可用的生成模型
  getGenerationModels: () => {
    return api.get('/generation/models')
  },
  
  // 生成文本
  generateText: (prompt, modelId, searchResults = [], options = {}) => {
    return api.post('/generation/generate', {
      prompt,
      model_id: modelId,
      search_results: searchResults,
      options
    })
  },
  
  // 获取生成历史
  getGenerationHistory: () => {
    return api.get('/generation/history')
  },
  
  // 获取特定生成结果
  getGenerationResult: (generationId) => {
    return api.get(`/generation/${generationId}`)
  },
  
  // 保存生成结果
  saveGenerationResult: (generationId, title) => {
    return api.post(`/generation/${generationId}/save`, {
      title
    })
  }
}

// RAG系统评估API
export const evaluationApi = {
  // 提交评估任务
  submitEvaluation: (formData) => {
    return api.post('/evaluation/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 300000 // 5分钟超时，因为评估可能需要较长时间
    })
  },
  
  // 获取评估结果
  getEvaluationResult: (evaluationId) => {
    return api.get(`/evaluation/result/${evaluationId}`)
  },
  
  // 获取评估历史
  getEvaluationHistory: () => {
    return api.get('/evaluation/history')
  },
  
  // 删除评估结果
  deleteEvaluation: (evaluationId) => {
    return api.delete(`/evaluation/${evaluationId}`)
  },
  
  // 下载评估报告
  downloadEvaluationReport: (evaluationId, format = 'json') => {
    window.open(`/api/evaluation/${evaluationId}/download?format=${format}`, '_blank')
    return Promise.resolve({ success: true })
  }
}

// RAG检索器评估API
export const ragRetrieverEvaluationApi = {
  // 提交检索器评估
  submitRetrieverEvaluation: (formData) => {
    return api.post('/rag-retriever-evaluation/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 300000 // 5分钟超时
    })
  }
}

// RAG生成器评估API
export const ragGeneratorEvaluationApi = {
  // 提交生成器评估
  submitGeneratorEvaluation: (formData) => {
    return api.post('/rag-generator-evaluation/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 300000 // 5分钟超时
    })
  }
}

export default api 