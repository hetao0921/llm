import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { generationApi } from '../services/api'

export const useGenerationStore = defineStore('generation', {
  state: () => ({
    generationModels: [],
    generationHistory: [],
    currentGeneration: null,
    loading: false,
    generating: false,
    error: null
  }),

  getters: {
    modelsList: (state) => {
      return state.generationModels || []
    },
    historyList: (state) => {
      return state.generationHistory || []
    },
    currentResult: (state) => {
      return state.currentGeneration
    }
  },

  actions: {
    async fetchGenerationModels() {
      this.loading = true
      this.error = null
      
      try {
        const response = await generationApi.getGenerationModels()
        this.generationModels = response.data
        return this.generationModels
      } catch (err) {
        this.error = err.response?.data?.detail || '获取生成模型列表失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async generateText(prompt, modelId, searchResults = [], options = {}) {
      this.generating = true
      this.error = null
      
      try {
        const response = await generationApi.generateText(prompt, modelId, searchResults, options)
        this.currentGeneration = response.data
        return this.currentGeneration
      } catch (err) {
        this.error = err.response?.data?.detail || '文本生成失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.generating = false
      }
    },
    
    async fetchGenerationHistory() {
      this.loading = true
      this.error = null
      
      try {
        const response = await generationApi.getGenerationHistory()
        this.generationHistory = response.data
        return this.generationHistory
      } catch (err) {
        this.error = err.response?.data?.detail || '获取生成历史失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async fetchGenerationResult(generationId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await generationApi.getGenerationResult(generationId)
        this.currentGeneration = response.data
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || '获取生成结果详情失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async saveGenerationResult(generationId, title) {
      this.loading = true
      this.error = null
      
      try {
        const response = await generationApi.saveGenerationResult(generationId, title)
        ElMessage.success('生成结果保存成功')
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || '保存生成结果失败'
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    }
  }
}) 