import { defineStore } from 'pinia'
import { loadingApi } from '../services/api'
import { ElMessage } from 'element-plus'

export const useLoadingStore = defineStore('loading', {
  state: () => ({
    files: [],
    currentFile: null,
    selectedFile: null,
    loading: false,
    error: null,
    processingFile: null,
  }),

  getters: {
    getFileById: (state) => (id) => {
      return state.files.find(file => file.id === id)
    },
    sortedFiles: (state) => {
      return [...state.files].sort((a, b) => {
        // Sort by upload time in descending order
        return new Date(b.upload_time) - new Date(a.upload_time)
      })
    },
    // 添加获取加载文件的getter
    getLoadedFiles: (state) => {
      console.log('Loading store: getLoadedFiles called, files count:', state.files.length)
      console.log('Files data:', JSON.stringify(state.files))
      return state.files
    }
  },

  actions: {
    async fetchFiles() {
      this.loading = true
      this.error = null
      
      try {
        console.log('Loading store: fetchFiles called')
        const response = await loadingApi.getFiles()
        console.log('Loading store: fetchFiles response:', response.data)
        if (response && response.data && Array.isArray(response.data.files)) {
          this.files = response.data.files.map(file => ({
            ...file,
            id: file.file_id // 确保id字段存在
          }))
        } else {
          console.warn('Loading store: Invalid response format in fetchFiles')
          this.files = []
        }
        console.log('Loading store: files after fetch:', this.files.length, 'files')
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load files'
        console.error('Error fetching files:', error)
        ElMessage.error(this.error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // 添加获取已加载文件列表的方法
    async fetchLoadedFiles() {
      this.loading = true
      this.error = null
      
      try {
        console.log('Loading store: fetchLoadedFiles called')
        const response = await loadingApi.getUploadedFiles()
        console.log('Loading store: fetchLoadedFiles response:', response.data)
        
        if (response && response.data && Array.isArray(response.data.files)) {
          this.files = response.data.files.map(file => ({
            ...file,
            id: file.file_id // 确保id字段存在
          }))
          console.log('Loading store: Mapped files:', this.files)
        } else {
          console.warn('Loading store: Invalid response format in fetchLoadedFiles, response:', response.data)
          this.files = []
        }
        
        console.log('Loading store: Updated files array with', this.files.length, 'files')
        return this.files
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load files'
        console.error('Error fetching loaded files:', error)
        ElMessage.error(this.error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async uploadFile(file, loader = 'auto') {
      this.loading = true
      this.error = null
      
      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('loader', loader)
        
        console.log('Loading store: uploadFile called with file', file.name)
        const response = await loadingApi.uploadFile(formData)
        console.log('Loading store: uploadFile response:', response.data)
        
        if (response && response.data) {
          await this.fetchFiles()
          ElMessage.success(`文件 '${file.name}' 上传成功`)
          return response.data
        }
      } catch (error) {
        this.error = error.response?.data?.detail || '文件上传失败'
        console.error('Upload error:', error)
        ElMessage.error(this.error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async loadDocument(fileId, loaderType, additionalParams = {}) {
      this.processingFile = fileId
      this.error = null
      
      try {
        console.log('Loading store: loadDocument called for fileId', fileId)
        const response = await loadingApi.loadDocument(fileId, loaderType, additionalParams)
        console.log('Loading store: loadDocument response:', response.data)
        
        // Update the file in the files array
        const index = this.files.findIndex(file => file.file_id === fileId)
        if (index !== -1) {
          this.files[index] = response.data.data || response.data
          console.log('Loading store: Updated file in files array')
        }
        
        ElMessage.success('Document loaded successfully')
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || 'Failed to load document'
        console.error('Error loading document:', err)
        ElMessage.error(this.error)
        throw err
      } finally {
        this.processingFile = null
      }
    },
    
    async getFileDetails(fileId) {
      this.loading = true
      this.error = null
      
      try {
        console.log('Loading store: getFileDetails called for fileId', fileId)
        const response = await loadingApi.getFileDetails(fileId)
        console.log('Loading store: getFileDetails response:', response.data)
        this.selectedFile = response.data.data || response.data
        return response.data
      } catch (err) {
        this.error = err.response?.data?.detail || 'Failed to get file details'
        console.error('Error getting file details:', err)
        ElMessage.error(this.error)
        throw err
      } finally {
        this.loading = false
      }
    },
    
    async deleteFile(fileId) {
      this.loading = true
      this.error = null
      
      try {
        console.log('Loading store: deleteFile called for fileId', fileId)
        const response = await loadingApi.deleteFile(fileId)
        console.log('Loading store: deleteFile response:', response.data)
        await this.fetchFiles()
        
        if (this.selectedFile && this.selectedFile.file_id === fileId) {
          this.selectedFile = null
          console.log('Loading store: Cleared selectedFile')
        }
        
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete file'
        console.error('Error deleting file:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    selectFile(file) {
      console.log('Loading store: selectFile called with file', file)
      this.selectedFile = file
    },

    setCurrentFile(file) {
      console.log('Loading store: setCurrentFile called with file', file)
      this.currentFile = file
    }
  }
}) 