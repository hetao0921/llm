import { defineStore } from 'pinia'
import { parsingApi } from '../services/api'
import { ElMessage } from 'element-plus'

export const useParsingStore = defineStore('parsing', {
  state: () => ({
    parsingResults: {},
    currentParsingId: null,
    currentResult: null,
    parsingHistory: {},
    availableMethods: {},
    loading: false,
    error: null,
    processingFileId: null
  }),

  getters: {
    getResultById: (state) => (parsingId) => {
      return state.parsingResults[parsingId] || null
    },
    
    getHistoryByFileId: (state) => (fileId) => {
      return state.parsingHistory[fileId] || []
    },
    
    getMethodsByFileId: (state) => (fileId) => {
      return state.availableMethods[fileId] || {}
    }
  },

  actions: {
    async parseDocument(fileId, parseMethod = 'full_text', includeTables = false) {
      this.processingFileId = fileId
      this.loading = true
      this.error = null

      try {
        const response = await parsingApi.parseDocument(fileId, parseMethod, includeTables)
        
        // 获取解析结果
        await this.getParsingResult(response.data.parsing_id)
        
        // 更新历史记录
        await this.getParsingHistory(fileId)
        
        ElMessage.success(`文档解析成功！`)
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || '文档解析失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
        this.processingFileId = null
      }
    },
    
    async getParsingResult(parsingId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await parsingApi.getParsingResult(parsingId)
        
        this.parsingResults = {
          ...this.parsingResults,
          [parsingId]: response.data
        }
        
        this.currentParsingId = parsingId
        this.currentResult = response.data
        
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || '获取解析结果失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async getAvailableMethods(fileId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await parsingApi.getAvailableMethods(fileId)
        
        this.availableMethods = {
          ...this.availableMethods,
          [fileId]: response.data.available_methods
        }
        
        return response.data.available_methods
      } catch (err) {
        this.error = err.response?.data?.detail || '获取可用解析方法失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async getParsingHistory(fileId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await parsingApi.getParsingHistory(fileId)
        
        this.parsingHistory = {
          ...this.parsingHistory,
          [fileId]: response.data.history
        }
        
        return response.data.history
      } catch (err) {
        this.error = err.response?.data?.detail || '获取解析历史失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    downloadResult(parsingId, format = 'json') {
      try {
        return parsingApi.downloadParsingResult(parsingId, format)
      } catch (err) {
        this.error = '下载解析结果失败'
        ElMessage.error(this.error)
        throw err
      }
    },
    
    clearResult() {
      this.currentParsingId = null
      this.currentResult = null
    }
  }
}) 