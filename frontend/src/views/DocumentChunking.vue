<template>
  <div class="document-chunking">
    <h1>文档分块</h1>
    <p>将文档分割成可管理的块，以便更好地检索和处理。分块结果保存为结构化JSON格式。</p>
    
    <el-card class="welcome-card" v-if="!selectedFileId">
      <div class="welcome-content">
        <h2>欢迎使用文档分块功能</h2>
        <p>本页面将帮助您将文档分割成更小的块，以便于后续的处理和查询。</p>
        
        <h3>使用步骤：</h3>
        <ol>
          <li>首先在<router-link to="/file-loading">文件加载</router-link>页面上传文档</li>
          <li>在本页面选择已上传的文档</li>
          <li>选择分块策略和参数</li>
          <li>点击"开始分块"按钮</li>
          <li>查看和管理生成的文档块</li>
        </ol>
      </div>
    </el-card>
    
    <div class="debug-info" style="margin: 20px 0; padding: 10px; border: 1px solid #ddd;">
      <h3>调试信息</h3>
      <div><strong>页面加载状态:</strong> {{ loading ? '加载中...' : '加载完成' }}</div>
      <div><strong>上传文件数量:</strong> {{ uploadedFiles?.length || 0 }}</div>
      <div><strong>选中文件ID:</strong> {{ selectedFileId || '无' }}</div>
      <div><strong>文档块数量:</strong> {{ documentChunks?.length || 0 }}</div>
      <div>
        <strong>文件列表:</strong>
        <ul v-if="uploadedFiles && uploadedFiles.length">
          <li v-for="file in uploadedFiles" :key="file.file_id">
            {{ file.filename }} (ID: {{ file.file_id }})
          </li>
        </ul>
        <div v-else>无上传文件</div>
      </div>
      <div>
        <el-button @click="refreshData" type="primary" size="small">刷新数据</el-button>
      </div>
    </div>
    
    <!-- 文档选择部分 -->
    <div class="select-document">
      <h2>1. 选择文档</h2>
      <div v-if="loading" class="loading">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="uploadedFiles.length === 0">
        <el-alert
          title="没有可用的文档"
          description="请先在文件加载页面上传并加载文档。上传后，还需要点击'加载文档'按钮处理文件。"
          type="info"
          :closable="false"
          show-icon>
          <template #default>
            <p>请按照以下步骤操作：</p>
            <ol>
              <li>前往<router-link to="/file-loading">文件加载</router-link>页面</li>
              <li>点击"上传文件"按钮，选择要上传的文档</li>
              <li>上传成功后，点击文件旁边的"加载文档"按钮</li>
              <li>加载完成后，返回本页面选择已加载的文档</li>
            </ol>
            <el-button type="primary" @click="goToFileLoading">前往文件加载页面</el-button>
          </template>
        </el-alert>
      </div>
      <div v-else class="document-selector">
        <el-select v-model="selectedFileId" placeholder="选择一个文档" style="width: 100%">
          <el-option
            v-for="file in uploadedFiles"
            :key="file.file_id"
            :label="file.filename"
            :value="file.file_id"
          />
        </el-select>
        <div class="hint" style="margin-top: 10px;">
          如果您刚上传的文档没有出现在列表中，请确保您已在<router-link to="/file-loading">文件加载</router-link>页面点击了"加载文档"按钮。
        </div>
      </div>
    </div>
    
    <!-- 分块配置 -->
    <el-card v-if="selectedFileId" class="chunking-config">
      <template #header>
        <div class="card-header">
          <span><h2>2. 配置分块策略</h2></span>
        </div>
      </template>
      
      <!-- 分块策略选择 -->
      <div class="strategy-select">
        <el-form label-position="top">
          <el-form-item label="分块策略:">
            <el-select v-model="selectedStrategy" @change="onStrategyChange" placeholder="选择策略" style="width: 100%">
              <el-option label="固定大小（字符数）" value="fixed_size" />
              <el-option label="按句子长度" value="sentence" />
              <el-option label="按段落" value="paragraph" />
              <el-option label="按页面" value="page" />
            </el-select>
          </el-form-item>
          
          <!-- 策略说明 -->
          <el-alert
            v-if="selectedStrategy === 'fixed_size'"
            title="固定大小分块"
            description="将文本分割成固定字符数的块，可设置重叠部分。"
            type="info"
            :closable="false"
          />
          <el-alert
            v-else-if="selectedStrategy === 'sentence'"
            title="基于句子的分块"
            description="将文本分成包含特定句子数量的块。"
            type="info"
            :closable="false"
          />
          <el-alert
            v-else-if="selectedStrategy === 'paragraph'"
            title="基于段落的分块"
            description="将文本分成包含特定段落数量的块。"
            type="info"
            :closable="false"
          />
          <el-alert
            v-else-if="selectedStrategy === 'page'"
            title="基于页面的分块"
            description="按页面边界分割文本（适用于PDF等基于页面的文档）。"
            type="info"
            :closable="false"
          />
          
          <!-- 字符分块设置 -->
          <template v-if="selectedStrategy === 'fixed_size'">
            <el-form-item label="块大小（字符数）:">
              <el-input-number v-model="chunkSize" :min="100" :max="10000" :step="100" />
              <div class="hint">推荐：1000字符</div>
            </el-form-item>
            <el-form-item label="重叠部分（字符数）:">
              <el-input-number v-model="chunkOverlap" :min="0" :max="chunkSize/2" :step="50" />
              <div class="hint">推荐：100-200字符</div>
            </el-form-item>
          </template>
          
          <!-- 句子分块设置 -->
          <template v-if="selectedStrategy === 'sentence'">
            <el-form-item label="每块句子数:">
              <el-input-number v-model="chunkSize" :min="1" :max="30" :step="1" />
              <div class="hint">推荐：5-10句</div>
            </el-form-item>
            <el-form-item label="句子重叠:">
              <el-input-number v-model="chunkOverlap" :min="0" :max="5" :step="1" />
              <div class="hint">推荐：1-2句</div>
            </el-form-item>
          </template>
          
          <!-- 段落分块设置 -->
          <template v-if="selectedStrategy === 'paragraph'">
            <el-form-item label="每块段落数:">
              <el-input-number v-model="chunkSize" :min="1" :max="20" :step="1" />
              <div class="hint">推荐：2-5段</div>
            </el-form-item>
            <el-form-item label="段落重叠:">
              <el-input-number v-model="chunkOverlap" :min="0" :max="3" :step="1" />
              <div class="hint">推荐：1段</div>
            </el-form-item>
          </template>
          
          <!-- 页面分块设置 -->
          <template v-if="selectedStrategy === 'page'">
            <el-form-item>
              <el-checkbox v-model="includePageMarkers">在块中包含页面标记</el-checkbox>
              <div class="hint">启用后，页码或标记将包含在块文本中</div>
            </el-form-item>
          </template>
          
          <el-form-item>
            <el-button type="primary" @click="onChunkDocument" :loading="processing">
              开始分块
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    
    <!-- 块显示 -->
    <el-card v-if="documentChunks && documentChunks.length" class="chunks-display">
      <template #header>
        <div class="card-header">
          <h2>文档块</h2>
          <el-tag type="success">{{ documentChunks.length }} 个块</el-tag>
        </div>
      </template>
      
      <div class="action-buttons">
        <el-button type="primary" @click="downloadJsonResults" size="small" style="margin-right: 10px">
          下载JSON结果
        </el-button>
        <el-button type="primary" @click="previewJsonResults" size="small" style="margin-right: 10px">
          预览JSON内容
        </el-button>
        <el-button type="danger" @click="deleteChunks" size="small">
          删除分块
        </el-button>
      </div>
      
      <el-table :data="documentChunks" border style="width: 100%">
            <el-table-column label="块编号" width="100">
              <template #default="scope">
            {{ scope.$index + 1 }}
              </template>
            </el-table-column>
            <el-table-column label="大小" width="120">
              <template #default="scope">
            {{ scope.row.size }} 字符
          </template>
        </el-table-column>
        <el-table-column label="预览" min-width="300">
          <template #default="scope">
            <div class="chunk-preview-short">
              {{ getPreviewText(scope.row.text) }}
            </div>
              </template>
            </el-table-column>
        <el-table-column label="操作" width="120">
              <template #default="scope">
            <el-button
              size="small"
              type="primary"
              @click="previewChunkContent(scope.row)"
            >
              预览内容
            </el-button>
              </template>
            </el-table-column>
          </el-table>
    </el-card>
    
    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="块内容预览"
      width="60%"
      :close-on-click-modal="false"
    >
      <div v-if="selectedChunk" class="chunk-preview-dialog">
        <pre>{{ selectedChunk.text }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { useChunkingStore } from '../store/chunking'
import { useLoadingStore } from '../store/loading'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'DocumentChunking',
  data() {
    return {
      // 加载状态
      loading: false,
      processing: false,
      
      // 文件列表
      uploadedFiles: [],
      selectedFileId: '',
      
      // 分块策略
      selectedStrategy: 'fixed_size',
      chunkSize: 1000,
      chunkOverlap: 200,
      includePageMarkers: true,
      
      // 分块结果
      documentChunks: [],
      
      // 预览设置
      previewDialogVisible: false,
      selectedChunk: null
    }
  },
  methods: {
    // 刷新数据
    async refreshData() {
      console.log('刷新数据')
      this.loading = true
      
      try {
        // 初始化存储
    const loadingStore = useLoadingStore()
    const chunkingStore = useChunkingStore()

        // 获取文件列表
        await loadingStore.fetchLoadedFiles()
        this.uploadedFiles = loadingStore.getLoadedFiles
        
        // 获取分块策略
        await chunkingStore.fetchChunkingStrategies()
        
        // 如果已选择文件，获取分块
        if (this.selectedFileId) {
          await this.fetchChunks()
        }
        
        ElMessage.success('数据已刷新')
      } catch (error) {
        console.error('刷新数据失败:', error)
        ElMessage.error('刷新数据失败')
      } finally {
        this.loading = false
      }
    },
    
    // 前往文件加载页面
    goToFileLoading() {
      this.$router.push('/file-loading')
    },
    
    // 获取分块
    async fetchChunks() {
      if (!this.selectedFileId) return
      
      this.loading = true
      try {
        const chunkingStore = useChunkingStore()
        await chunkingStore.fetchDocumentChunks(this.selectedFileId)
        this.documentChunks = chunkingStore.getChunksByFileId(this.selectedFileId)
        console.log('获取到分块:', this.documentChunks)
      } catch (error) {
        console.error('获取分块失败:', error)
        ElMessage.error('获取分块失败')
      } finally {
        this.loading = false
      }
    },
    
    // 策略改变
    onStrategyChange() {
      switch (this.selectedStrategy) {
        case 'fixed_size':
          this.chunkSize = 1000
          this.chunkOverlap = 200
          break
        case 'sentence':
          this.chunkSize = 5
          this.chunkOverlap = 1
          break
        case 'paragraph':
          this.chunkSize = 3
          this.chunkOverlap = 1
          break
        case 'page':
          this.includePageMarkers = true
          break
      }
    },
    
    // 分块文档
    async onChunkDocument() {
      if (!this.selectedFileId) {
        ElMessage.warning('请先选择一个文档')
        return
      }
      
      this.processing = true
      try {
        // 修复文件ID格式，删除可能存在的路径和文件扩展名
        let fileId = this.selectedFileId
        // 如果ID中包含路径分隔符，取最后一部分
        if (fileId.includes('/') || fileId.includes('\\')) {
          fileId = fileId.split(/[\/\\]/).pop()
        }
        // 如果ID中包含下划线和日期/时间格式，提取UUID部分
        if (fileId.includes('_')) {
          const parts = fileId.split('_')
          // 尝试寻找类似UUID格式的部分
          for (const part of parts) {
            if (part.includes('-') && part.length > 30) {
              fileId = part
              break
            }
          }
        }
        
        console.log('处理后的文件ID:', fileId)
        
        // 根据选择的策略准备参数
        const params = this.selectedStrategy === 'page'
          ? { include_page_markers: this.includePageMarkers }
          : { chunk_size: this.chunkSize, chunk_overlap: this.chunkOverlap }
        
        // 执行分块
        const chunkingStore = useChunkingStore()
        await chunkingStore.chunkDocument(fileId, this.selectedStrategy, params)
        
        // 获取分块结果
        await this.fetchChunks()
        ElMessage.success('文档分块完成')
      } catch (error) {
        console.error('分块失败:', error)
        ElMessage.error('分块失败，请尝试重新启动服务并刷新页面')
      } finally {
        this.processing = false
      }
    },
    
    // 获取预览文本
    getPreviewText(text) {
      const maxLength = 100
      if (!text) return ''
      if (text.length <= maxLength) return text
      return text.substring(0, maxLength) + '...'
    },
    
    // 预览块内容
    previewChunkContent(chunk) {
      this.selectedChunk = chunk
      this.previewDialogVisible = true
    },

    // 下载JSON结果
    async downloadJsonResults() {
      if (!this.selectedFileId) return
      
      try {
        const chunkingStore = useChunkingStore()
        const response = await chunkingStore.fetchChunksJson(this.selectedFileId)
        
        if (response) {
          const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' })
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `chunks_${this.selectedFileId}.json`
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          document.body.removeChild(a)
        }
      } catch (error) {
        console.error('下载失败:', error)
        ElMessage.error('下载失败')
      }
    },
    
    // 预览JSON内容
    async previewJsonResults() {
      if (!this.selectedFileId) return
      
      try {
        const chunkingStore = useChunkingStore()
        const response = await chunkingStore.fetchChunksJson(this.selectedFileId)
        
        if (response) {
          ElMessageBox.alert(JSON.stringify(response, null, 2), 'JSON预览', {
            customClass: 'json-preview-dialog'
          })
        }
      } catch (error) {
        console.error('预览失败:', error)
        ElMessage.error('预览失败')
      }
    },
    
    // 删除分块
    async deleteChunks() {
      if (!this.selectedFileId) return
      
      try {
        await ElMessageBox.confirm('确定要删除当前文档的所有分块吗？', '警告', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const chunkingStore = useChunkingStore()
        await chunkingStore.deleteDocumentChunks(this.selectedFileId)
        this.documentChunks = []
        ElMessage.success('分块已删除')
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除失败:', error)
          ElMessage.error('删除失败')
        }
      }
    }
  },
  async mounted() {
    console.log('DocumentChunking 组件已加载')
    await this.refreshData()
  }
}
</script>

<style scoped>
.document-chunking {
  padding: 20px;
}

.welcome-card {
  margin-bottom: 20px;
}

.welcome-content {
  padding: 10px;
}

.welcome-content h2 {
  color: #409eff;
  margin-top: 0;
}

.welcome-content h3 {
  margin-top: 20px;
  margin-bottom: 10px;
}

.welcome-content ol {
  padding-left: 20px;
}

.welcome-content li {
  margin-bottom: 8px;
}

.select-document {
  margin-bottom: 20px;
}

.chunking-config {
  margin-bottom: 20px;
}

.hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.chunks-display {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-buttons {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

.chunk-preview-short {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: monospace;
}

.chunk-preview-dialog {
  max-height: 60vh;
  overflow-y: auto;
}

.chunk-preview-dialog pre {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 15px;
  white-space: pre-wrap;
  word-wrap: break-word;
  border: 1px solid #e4e7ed;
  font-family: monospace;
}

.json-preview-dialog {
  font-family: monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style> 