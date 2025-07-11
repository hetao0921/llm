import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { indexingApi } from '../services/api'

export const useIndexingStore = defineStore('indexing', {
  state: () => ({
    vectorDatabases: [],
    indices: [],
    currentIndex: null,
    searchResults: [],
    searchHistory: [],
    loading: false,
    processing: false,
    error: null
  }),

  getters: {
    databasesList: (state) => {
      return state.vectorDatabases || []
    },
    indicesList: (state) => {
      return state.indices || []
    },
    currentSearchResults: (state) => {
      return state.searchResults || []
    },
    searchHistoryList: (state) => {
      return state.searchHistory || []
    }
  },

  actions: {
    async fetchVectorDatabases() {
      this.loading = true
      this.error = null
      
      try {
        const response = await indexingApi.getVectorDatabases()
        this.vectorDatabases = response.data
        return this.vectorDatabases
      } catch (err) {
        this.error = err.response?.data?.detail || '获取向量数据库列表失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async createIndex(embeddingId, dbType, indexName, config = {}) {
      this.processing = true
      this.error = null
      
      try {
        const response = await indexingApi.createIndex(embeddingId, dbType, indexName, config)
        ElMessage.success('索引创建成功')
        await this.fetchIndices()
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || '创建索引失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.processing = false
      }
    },
    
    async fetchIndices() {
      this.loading = true
      this.error = null
      
      try {
        const response = await indexingApi.getIndices()
        this.indices = response.data
        return this.indices
      } catch (err) {
        this.error = err.response?.data?.detail || '获取索引列表失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async fetchIndexDetails(indexId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await indexingApi.getIndexDetails(indexId)
        this.currentIndex = response.data
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || '获取索引详情失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async deleteIndex(indexId) {
      this.processing = true
      this.error = null
      
      try {
        await indexingApi.deleteIndex(indexId)
        ElMessage.success('索引删除成功')
        
        // 更新索引列表
        this.indices = this.indices.filter(index => index.id !== indexId)
        
        if (this.currentIndex && this.currentIndex.id === indexId) {
          this.currentIndex = null
        }
        
        return true
      } catch (err) {
        this.error = err.response?.data?.detail || '删除索引失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.processing = false
      }
    },
    
    async searchIndex(indexId, query, topK = 5, filter = {}) {
      this.loading = true
      this.error = null
      
      try {
        const response = await indexingApi.searchIndex(indexId, query, topK, filter)
        this.searchResults = response.data.results
        return this.searchResults
      } catch (err) {
        this.error = err.response?.data?.detail || '搜索失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async saveSearchResult(searchId) {
      this.processing = true
      this.error = null
      
      try {
        const response = await indexingApi.saveSearchResult(searchId)
        ElMessage.success('搜索结果已保存')
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || '保存搜索结果失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.processing = false
      }
    },
    
    async fetchSearchHistory() {
      this.loading = true
      this.error = null
      
      try {
        const response = await indexingApi.getSearchHistory()
        this.searchHistory = response.data
        return this.searchHistory
      } catch (err) {
        this.error = err.response?.data?.detail || '获取搜索历史失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    }
  }
}) 