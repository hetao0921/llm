<template>
  <div class="file-loading">
    <h1>文件加载</h1>
    <p>上传并处理文档。</p>
    
    <el-card class="upload-section">
      <template #header>
        <div class="card-header">
          <span>上传文档</span>
        </div>
      </template>
      
      <div class="upload-area">
        <el-form label-position="top">
          <el-form-item label="选择文档加载器">
            <el-select v-model="selectedLoader" placeholder="选择加载器">
              <el-option label="自动选择" value="auto" />
              <el-option label="PyMuPDF (PDF)" value="pymupdf" />
              <el-option label="PyPDF (PDF)" value="pypdf" />
              <el-option label="Unstructured (多格式)" value="unstructured" />
              <el-option label="DOCX (Word文档)" value="docx" />
              <el-option label="Text (文本文件)" value="text" />
            </el-select>
            <div class="hint">根据文件类型自动选择最合适的加载器</div>
          </el-form-item>
          
        <el-upload
          class="upload-demo"
            action="/api/loading/files/upload"
            :headers="{
              'Accept': 'application/json'
            }"
          :auto-upload="false"
          :on-change="handleFileChange"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
          :limit="1"
            :data="{ loader: selectedLoader }"
        >
          <template #trigger>
            <el-button type="primary">选择文件</el-button>
          </template>
          <el-button
            class="ml-3"
            type="success"
            :disabled="!selectedFile"
            @click="uploadFile"
          >
            上传文件
          </el-button>
        </el-upload>
        </el-form>
      </div>
    </el-card>
    
    <el-card class="files-section" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>已上传文件</span>
          <el-button type="primary" @click="refreshFiles">刷新列表</el-button>
        </div>
      </template>
      
      <div v-if="files.length === 0" class="no-files">
        <el-empty description="暂无文件" />
      </div>
      <div v-else class="files-list">
        <el-table :data="files" style="width: 100%">
          <el-table-column prop="original_filename" label="文件名" />
          <el-table-column prop="file_type" label="类型" width="120" />
          <el-table-column label="大小" width="120">
            <template #default="scope">
              {{ formatFileSize(scope.row.size_bytes) }}
            </template>
          </el-table-column>
          <el-table-column label="上传时间" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.upload_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="250">
            <template #default="scope">
              <el-button
                size="small"
                type="primary"
                @click="previewFile(scope.row)"
              >
                预览
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="deleteFile(scope.row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
    
    <!-- 文件预览对话框 -->
    <el-dialog
      v-model="showFilePreview"
      :title="previewTitle"
      width="80%"
      @closed="handlePreviewClose"
    >
      <div v-if="previewLoading" class="loading-preview">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else>
        <div v-if="previewType === 'text'" class="text-preview">
          <pre>{{ previewContent }}</pre>
        </div>
        <div v-else-if="previewType === 'pdf'" class="pdf-preview">
          <div class="pdf-controls">
            <el-pagination
              v-if="totalPages > 1"
              layout="prev, pager, next"
              :total="totalPages"
              :current-page="currentPage"
              @current-change="changePdfPage"
            />
          </div>
          <div class="pdf-content" v-html="previewContent"></div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useLoadingStore } from '../store/loading'
import { ElMessage, ElMessageBox } from 'element-plus'
import { loadingApi } from '../services/api'

const loadingStore = useLoadingStore()
const loading = ref(false)
const selectedFile = ref(null)
const files = computed(() => loadingStore.sortedFiles)
const selectedLoader = ref('auto')

// 计算上传路径
const uploadUrl = computed(() => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl}/api/loading/files/upload`
})

// 预览相关
const showFilePreview = ref(false)
const previewTitle = ref('')
const previewContent = ref('')
const previewLoading = ref(false)
const previewType = ref('text')
const currentPage = ref(1)
const totalPages = ref(1)
const previewFileId = ref(null)

onMounted(async () => {
  await refreshFiles()
})

const refreshFiles = async () => {
  loading.value = true
  try {
    await loadingStore.fetchFiles()
  } catch (error) {
    console.error('Error loading files:', error)
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const uploadFile = async () => {
  if (!selectedFile.value) return
  
  loading.value = true
  try {
    await loadingStore.uploadFile(selectedFile.value, selectedLoader.value)
    selectedFile.value = null
    await refreshFiles()
    ElMessage.success('文件上传成功')
  } catch (error) {
    console.error('Upload error:', error)
    ElMessage.error('文件上传失败')
  } finally {
    loading.value = false
  }
}

const deleteFile = async (file) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件 "${file.original_filename}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await loadingStore.deleteFile(file.file_id)
    if (response && response.status === 'partial') {
      ElMessage.warning({
        message: '文件部分删除成功，但有一些错误发生：\n' + response.errors.join('\n'),
        duration: 5000
      })
    } else if (response && response.status === 'success') {
      ElMessage.success(response.message || '文件删除成功')
    }
    await refreshFiles()
  } catch (error) {
    if (error === 'cancel') {
      return
    }
    console.error('Delete error:', error)
    ElMessage.error('文件删除失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString()
}

const previewFile = async (file) => {
  previewLoading.value = true
  previewFileId.value = file.file_id
  previewTitle.value = file.original_filename
  showFilePreview.value = true
  currentPage.value = 1
  previewContent.value = ''  // 重置预览内容
  
  try {
    // 根据文件类型设置预览类型
    if (file.file_type === 'pdf') {
      previewType.value = 'pdf'
      totalPages.value = file.page_count || 1
      await getPdfPreview(file.file_id, 1)
    } else {
      previewType.value = 'text'
      const response = await loadingApi.getFilePreview(file.file_id)
      if (response && response.data) {
        previewContent.value = response.data.content || '无法预览文件内容'
      } else {
        previewContent.value = '无法预览文件内容'
        ElMessage.warning('无法获取文件预览内容')
      }
    }
  } catch (error) {
    console.error('Preview error:', error)
    previewContent.value = '加载预览失败: ' + (error.response?.data?.detail || error.message || '未知错误')
    ElMessage.error('文件预览失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    previewLoading.value = false
  }
}

const getPdfPreview = async (fileId, page) => {
  try {
    const response = await loadingApi.getFilePreview(fileId, page)
    if (response && response.data) {
      if (response.data.content) {
        previewContent.value = response.data.content
      } else {
        previewContent.value = '无法预览PDF内容'
        ElMessage.warning('PDF内容预览失败')
      }
    } else {
      previewContent.value = '无法预览PDF内容'
      ElMessage.warning('PDF内容预览失败')
    }
  } catch (error) {
    console.error('PDF preview error:', error)
    previewContent.value = '加载PDF预览失败: ' + (error.response?.data?.detail || error.message || '未知错误')
    ElMessage.error('PDF预览失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  }
}

const changePdfPage = async (page) => {
  if (page === currentPage.value) return
  
  currentPage.value = page
  previewLoading.value = true
  previewContent.value = ''  // 清空当前内容
  
  try {
    await getPdfPreview(previewFileId.value, page)
  } catch (error) {
    console.error('Change page error:', error)
    ElMessage.error('切换页面失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    previewLoading.value = false
  }
}

// 监听预览对话框关闭
const handlePreviewClose = () => {
  previewContent.value = ''
  previewTitle.value = ''
  previewType.value = 'text'
  currentPage.value = 1
  totalPages.value = 1
  previewFileId.value = null
}

const handleUploadError = (err, file) => {
  console.error('Upload error:', err)
  ElMessage.error(`文件 ${file.name} 上传失败: ${err.message || '未知错误'}`)
}

const beforeUpload = (file) => {
  // 检查文件大小（默认限制为50MB）
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过50MB')
    return false
  }
  
  // 检查文件类型
  const allowedTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'text/plain',
    'text/markdown',
    'text/csv',
    'application/json',
    'text/html'
  ]
  
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  
  return true
}
</script>

<style scoped>
.file-loading {
  padding: 20px;
}

.upload-section,
.files-section {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-area {
  padding: 20px;
  text-align: center;
}

.no-files {
  padding: 40px;
  text-align: center;
}

.files-list {
  margin-top: 20px;
}

:deep(.el-upload-list) {
  margin-top: 20px;
}

.text-preview pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  font-family: monospace;
}

.pdf-preview {
  display: flex;
  flex-direction: column;
}

.pdf-controls {
  margin-bottom: 15px;
  text-align: center;
}

.loading-preview {
  padding: 20px;
}

.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style> 