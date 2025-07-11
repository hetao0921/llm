import { defineStore } from 'pinia'
import { chunkingApi } from '../services/api'
import { ElMessage } from 'element-plus'

export const useChunkingStore = defineStore('chunking', {
  state: () => ({
    // 分块策略列表
    strategies: [],
    
    // 文档分块结果
    documentChunks: {}, // 按文档ID组织的分块数据
    
    // 加载状态
    loading: false,
    
    // 处理状态
    processing: false,
    
    // 错误信息
    error: null
  }),

  getters: {
    // 获取分块策略列表
    getStrategies: (state) => {
      return state.strategies
    },
    
    // 获取特定文档的分块
    getChunksByFileId: (state) => (fileId) => {
      console.log('Chunking store: getChunksByFileId called for fileId:', fileId)
      console.log('Chunking store: Current documentChunks state:', state.documentChunks)
      
      // 检查文档ID是否存在
      if (!fileId || !state.documentChunks[fileId]) {
        console.log('Chunking store: No chunks found for this fileId')
        return []
      }
      
      // 获取分块数据，处理可能的不同数据结构
      let chunks = []
      if (state.documentChunks[fileId].chunks) {
        // 如果是 { chunks: [...] } 结构
        chunks = state.documentChunks[fileId].chunks
        console.log('Chunking store: Found chunks array in documentChunks[fileId].chunks:', chunks.length, 'chunks')
      } else if (Array.isArray(state.documentChunks[fileId])) {
        // 如果直接是数组
        chunks = state.documentChunks[fileId]
        console.log('Chunking store: documentChunks[fileId] is directly an array:', chunks.length, 'chunks')
      }
      
      if (!chunks || chunks.length === 0) {
        console.log('Chunking store: Empty chunks array returned')
        return []
      }
      
      // 确保每个块都有必要的属性
      const mappedChunks = chunks.map((chunk, index) => ({
        ...chunk,
        size: chunk.size || chunk.text?.length || 0,
        timestamp: chunk.timestamp || new Date().toISOString(),
        id: chunk.id || `chunk_${index}_${Math.random().toString(36).substring(2, 9)}`
      }))
      
      console.log('Chunking store: Returning', mappedChunks.length, 'processed chunks')
      return mappedChunks
    },
    
    // 获取分块信息
    getChunkingInfo: (state) => (fileId) => {
      if (!fileId || !state.documentChunks[fileId]) return null
      
      const chunkData = state.documentChunks[fileId]
      return {
        strategy: chunkData.strategy || '未知',
        params: chunkData.params || {},
        chunkCount: chunkData.chunks?.length || (Array.isArray(chunkData) ? chunkData.length : 0),
        originalSize: chunkData.original_size || 0,
        timestamp: chunkData.timestamp || new Date().toISOString()
      }
    },
    
    // 检查文档是否有分块
    hasChunks: (state) => (fileId) => {
      if (!fileId || !state.documentChunks[fileId]) return false
      
      // 检查不同的数据结构
      if (state.documentChunks[fileId].chunks) {
        return Array.isArray(state.documentChunks[fileId].chunks) && 
               state.documentChunks[fileId].chunks.length > 0
      }
      
      return Array.isArray(state.documentChunks[fileId]) && 
             state.documentChunks[fileId].length > 0
    }
  },

  actions: {
    // 获取分块策略列表
    async fetchChunkingStrategies() {
      this.loading = true
      this.error = null
      
      try {
        console.log('Chunking store: fetchChunkingStrategies called')
        const response = await chunkingApi.getChunkingStrategies()
        console.log('Chunking store: Fetched chunking strategies:', response.data)
        this.strategies = response.data || []
        return this.strategies
      } catch (error) {
        console.error('Chunking store: Failed to fetch chunking strategies:', error)
        this.error = error.response?.data?.detail || '获取分块策略失败'
        
        // 使用默认策略，确保UI不会崩溃
        this.strategies = [
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
        
        ElMessage.warning('无法获取分块策略，使用默认策略')
        return this.strategies
      } finally {
        this.loading = false
      }
    },
    
    // 获取文档分块
    async fetchDocumentChunks(fileId) {
      if (!fileId) return null
      
      this.loading = true
      this.error = null
      
      try {
        console.log('Chunking store: fetchDocumentChunks called for fileId:', fileId)
        const response = await chunkingApi.getDocumentChunks(fileId)
        console.log('Chunking store: Fetched chunks response:', response.data)
        
        if (response.data) {
          console.log('Chunking store: Response data structure:', JSON.stringify(response.data).substring(0, 200) + '...')
          
          // 处理不同的响应结构
          if (response.data.chunks) {
            // 如果是 { chunks: [...] } 结构
            console.log('Chunking store: Response has chunks property with', response.data.chunks.length, 'chunks')
            this.documentChunks[fileId] = {
              ...response.data,
              chunks: Array.isArray(response.data.chunks) ? response.data.chunks : [],
              timestamp: response.data.timestamp || new Date().toISOString()
            }
          } else if (Array.isArray(response.data)) {
            // 如果直接是数组
            console.log('Chunking store: Response is directly an array with', response.data.length, 'chunks')
            this.documentChunks[fileId] = {
              chunks: response.data,
              timestamp: new Date().toISOString()
            }
          } else {
            // 其他情况，创建一个空数组
            console.warn('Chunking store: Response has unexpected structure, creating empty array')
            this.documentChunks[fileId] = { chunks: [] }
          }
        } else {
          console.warn('Chunking store: No data in response, creating empty chunks array')
          this.documentChunks[fileId] = { 
            chunks: [],
            timestamp: new Date().toISOString()
          }
        }
        
        console.log('Chunking store: Updated documentChunks state for fileId:', fileId)
        return this.documentChunks[fileId]
      } catch (error) {
        console.error(`Chunking store: Failed to fetch document chunks for file ${fileId}:`, error)
        
        if (error.response?.status === 404) {
          console.warn('Chunking store: 404 response, creating empty chunks array')
          this.documentChunks[fileId] = { 
            chunks: [],
            timestamp: new Date().toISOString()
          }
          return { chunks: [] }
        }
        
        this.error = error.response?.data?.detail || '获取文档分块失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // 对文档进行分块
    async chunkDocument(fileId, strategy, params = {}) {
      if (!fileId) {
        console.error('Chunking store: No fileId provided for chunkDocument')
        throw new Error('No fileId provided')
      }
      
      this.processing = true
      this.error = null
      
      try {
        console.log('Chunking store: chunkDocument called with params:', { fileId, strategy, params })
        const response = await chunkingApi.chunkDocument(fileId, strategy, params)
        console.log('Chunking store: Chunk document response:', response.data)
        
        if (response.data) {
          // 处理不同的响应结构
          if (response.data.chunks) {
            // 如果是 { chunks: [...] } 结构
            console.log('Chunking store: Response has chunks property with', response.data.chunks.length, 'chunks')
            this.documentChunks[fileId] = {
              ...response.data,
              chunks: Array.isArray(response.data.chunks) ? response.data.chunks : [],
              timestamp: response.data.timestamp || new Date().toISOString(),
              strategy: strategy,
              params: params
            }
          } else if (Array.isArray(response.data)) {
            // 如果直接是数组
            console.log('Chunking store: Response is directly an array with', response.data.length, 'chunks')
            this.documentChunks[fileId] = {
              chunks: response.data,
              timestamp: new Date().toISOString(),
              strategy: strategy,
              params: params
            }
          } else {
            // 其他情况，创建一个空数组
            console.warn('Chunking store: Response has unexpected structure, creating empty array')
            this.documentChunks[fileId] = { 
              chunks: [],
              timestamp: new Date().toISOString(),
              strategy: strategy,
              params: params
            }
          }
        }
        
        console.log('Chunking store: Updated documentChunks after chunking for fileId:', fileId)
        return this.documentChunks[fileId]
      } catch (error) {
        console.error(`Chunking store: Failed to chunk document ${fileId}:`, error)
        
        // 添加更具体的错误处理
        if (error.response) {
          if (error.response.status === 404) {
            this.error = '找不到要分块的文件。请确保您已在文件加载页面上传并加载了文档。'
            ElMessage.error(this.error)
          } else if (error.response.status === 400) {
            this.error = error.response.data?.detail || '请求参数错误。请确保您已在文件加载页面正确加载了文档。'
            ElMessage.error(this.error)
          } else {
            this.error = error.response.data?.detail || '分块失败'
            ElMessage.error(this.error)
          }
        } else {
          this.error = '网络错误，无法连接到服务器'
        ElMessage.error(this.error)
        }
        
        throw error
      } finally {
        this.processing = false
      }
    },
    
    // 删除文档分块
    async deleteDocumentChunks(fileId) {
      if (!fileId) return null
      
      this.processing = true
      this.error = null
      
      try {
        console.log('Chunking store: deleteDocumentChunks called for fileId:', fileId)
        const response = await chunkingApi.deleteChunks(fileId)
        console.log('Chunking store: Delete response:', response.data)
        
        // 从状态中删除文档分块
        if (this.documentChunks[fileId]) {
          delete this.documentChunks[fileId]
          console.log('Chunking store: Removed chunks from store for fileId:', fileId)
        }
        
        return response.data
      } catch (error) {
        console.error(`Chunking store: Failed to delete document chunks for file ${fileId}:`, error)
        this.error = error.response?.data?.detail || '删除文档分块失败'
        ElMessage.error(this.error)
        throw error
      } finally {
        this.processing = false
      }
    },
    
    // 获取JSON格式的分块数据
    async fetchChunksJson(fileId) {
      if (!fileId) {
        console.error('Chunking store: No fileId provided for fetchChunksJson')
        throw new Error('No fileId provided')
      }
      
      try {
        console.log('Chunking store: fetchChunksJson called for fileId:', fileId)
        const response = await chunkingApi.getChunksJson(fileId)
        console.log('Chunking store: JSON response:', response.data)
        return response.data
      } catch (error) {
        console.error(`Chunking store: Failed to fetch chunks JSON for file ${fileId}:`, error)
        ElMessage.error('获取JSON格式分块数据失败')
        throw error
      }
    }
  }
}) 