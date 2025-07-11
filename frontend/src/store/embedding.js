import { defineStore } from 'pinia'
import { embeddingApi } from '../services/api'
import { ElMessage } from 'element-plus'

export const useEmbeddingStore = defineStore('embedding', {
  state: () => ({
    // 嵌入提供商列表
    providers: {},
    // 嵌入模型映射
    models: {},
    // 按文件ID组织的嵌入历史
    embeddingsByFileId: {},
    // JSON文件列表
    jsonFiles: [],
  }),
  
  getters: {
    // 获取提供商列表
    providersList() {
      return Object.entries(this.providers).map(([id, provider]) => ({
        id,
        ...provider
      }))
    },
    
    // 按提供商ID获取模型
    getModelsByProvider: (state) => (providerId) => {
      const models = Object.entries(state.models)
        .filter(([, model]) => model.provider_id === providerId)
        .map(([id, model]) => ({
          id,
          ...model
        }))
      
      return models
    },
    
    // 获取特定文件的嵌入列表
    getEmbeddingsByFileId: (state) => (fileId) => {
      return state.embeddingsByFileId[fileId] || []
    },
    
    // 获取所有嵌入列表
    allEmbeddings() {
      const allEmbeddings = []
      Object.values(this.embeddingsByFileId).forEach(embeddings => {
        allEmbeddings.push(...embeddings)
      })
      return allEmbeddings
    }
  },
  
  actions: {
    // 获取JSON文件列表
    async fetchJsonFiles() {
      try {
        const response = await embeddingApi.getJsonFiles()
        if (response && response.data) {
          this.jsonFiles = response.data
        }
        return this.jsonFiles
      } catch (error) {
        console.error('Error fetching JSON files:', error)
        ElMessage.error('获取JSON文件列表失败')
        throw error
      }
    },
    
    // 获取提供商列表
    async fetchProviders() {
      try {
        const response = await embeddingApi.getEmbeddingProviders()
        this.providers = response.data || {}
        return this.providers
      } catch (error) {
        console.error('Error fetching embedding providers:', error)
        ElMessage.error('获取嵌入提供商列表失败')
        throw error
      }
    },
    
    // 获取提供商的模型
    async fetchProviderModels(providerId) {
      try {
        const response = await embeddingApi.getProviderModels(providerId)
        
        // 更新模型，保留现有模型
        const newModels = response.data || {}
        for (const [id, model] of Object.entries(newModels)) {
          this.models[id] = model
        }
        
        return this.getModelsByProvider(providerId)
      } catch (error) {
        console.error(`Error fetching models for provider ${providerId}:`, error)
        ElMessage.error('获取嵌入模型列表失败')
        throw error
      }
    },
    
    // 创建嵌入
    async createEmbeddings(fileId, providerId, modelId, options = {}) {
      try {
        const response = await embeddingApi.createEmbeddings(
          fileId, providerId, modelId, options
        )
        
        // 添加新的嵌入到历史记录
        if (response.data) {
          if (!this.embeddingsByFileId[fileId]) {
            this.embeddingsByFileId[fileId] = []
          }
          
          // 检查是否已经存在相同ID的嵌入
          const existingIndex = this.embeddingsByFileId[fileId].findIndex(
            e => e.embedding_id === response.data.embedding_id
          )
          
          if (existingIndex >= 0) {
            // 更新现有嵌入
            this.embeddingsByFileId[fileId][existingIndex] = response.data
          } else {
            // 添加新嵌入
            this.embeddingsByFileId[fileId].push(response.data)
          }
        }
        
        return response.data
      } catch (error) {
        console.error('Error creating embeddings:', error)
        ElMessage.error('创建嵌入失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
        throw error
      }
    },
    
    // 获取嵌入历史
    async fetchEmbeddingHistory(fileId) {
      try {
        const response = await embeddingApi.getEmbeddingHistory(fileId)
        
        if (response.data) {
          this.embeddingsByFileId[fileId] = response.data
        } else {
          this.embeddingsByFileId[fileId] = []
        }
        
        return this.embeddingsByFileId[fileId]
      } catch (error) {
        console.error('Error fetching embedding history:', error)
        ElMessage.error('获取嵌入历史记录失败')
        throw error
      }
    }
  }
}) 