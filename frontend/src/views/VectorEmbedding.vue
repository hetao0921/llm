<template>
  <div class="vector-embedding">
    <h1>向量嵌入</h1>
    <p>将文本转换为向量表示，支持多种嵌入模型。</p>
    
    <div class="select-document">
      <h2>1. 选择JSON文件</h2>
      <div v-if="loading" class="loading">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="!jsonFiles || jsonFiles.length === 0">
        <el-alert
          title="没有可用的JSON文件"
          description="请先在文档分块页面处理文档，或上传JSON文件"
          type="info"
          :closable="false"
          show-icon
        />
      </div>
      <div v-else class="document-selector">
        <el-select v-model="selectedFileId" placeholder="选择一个JSON文件" style="width: 100%" @change="onFileChange">
          <el-option
            v-for="file in jsonFiles"
            :key="file.file_id"
            :label="file.filename"
            :value="file.file_id"
          >
            <div class="file-option">
              <span>{{ file.filename }}</span>
              <span v-if="file.type === 'chunks'" class="file-type">(分块文件: {{ file.chunks_count || 0 }}块)</span>
              <span v-else class="file-type">({{ file.type }})</span>
            </div>
          </el-option>
        </el-select>
        
        <!-- 显示文件信息 -->
        <div v-if="selectedFileId && selectedFile" class="file-info">
          <el-alert
            type="info"
            :closable="false"
            show-icon
          >
            <template #title>
              <span>文件信息</span>
            </template>
            <template #default>
              <p>文件名: {{ selectedFile.filename }}</p>
              <p>类型: {{ selectedFile.type }}</p>
              <p v-if="selectedFile.chunks_count">分块数量: {{ selectedFile.chunks_count }}</p>
              <p v-if="selectedFile.strategy">分块策略: {{ selectedFile.strategy }}</p>
            </template>
          </el-alert>
        </div>
      </div>
    </div>
    
    <el-card v-if="selectedFileId" class="embedding-config">
      <template #header>
        <div class="card-header">
          <span><h2>2. 配置嵌入模型</h2></span>
        </div>
      </template>
      
      <!-- 嵌入提供商选择 -->
      <div class="provider-select">
        <el-form label-position="top">
          <el-form-item label="嵌入提供商:">
            <el-select v-model="selectedProviderId" placeholder="选择提供商" style="width: 100%" @change="onProviderChange">
              <el-option 
                v-for="provider in providers"
                :key="provider.id"
                :label="provider.name"
                :value="provider.id"
                :disabled="!provider.available"
              />
            </el-select>
          </el-form-item>
          
          <!-- 提供商下的模型选择 -->
          <el-form-item v-if="selectedProviderId" label="嵌入模型:">
            <el-select v-model="selectedModelId" placeholder="选择模型" style="width: 100%">
              <el-option 
                v-for="model in providerModels"
                :key="model.id"
                :label="model.name"
                :value="model.id"
                :disabled="!model.available"
              />
            </el-select>
            <div class="hint" v-if="selectedModel">
              维度: {{ selectedModel.dimensions }}, 
              上下文长度: {{ selectedModel.context_length }}
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="createEmbedding" :loading="processing">
              创建嵌入
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    
    <!-- 嵌入历史 -->
    <el-card v-if="selectedFileId && embeddings.length > 0" class="embedding-history">
      <template #header>
        <div class="card-header">
          <span><h2>嵌入历史</h2></span>
        </div>
      </template>
      
      <el-table :data="embeddings" style="width: 100%" @row-click="showEmbeddingDetails">
        <el-table-column label="创建时间" width="180">
          <template #default="scope">
            {{ formatTimestamp(scope.row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column label="提供商" width="120">
          <template #default="scope">
            {{ scope.row.provider_name }}
          </template>
        </el-table-column>
        <el-table-column label="模型" width="150">
          <template #default="scope">
            {{ scope.row.model_name }}
          </template>
        </el-table-column>
        <el-table-column label="维度" width="100">
          <template #default="scope">
            {{ scope.row.dimensions }}
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="scope">
            <el-button type="primary" size="small" @click.stop="showEmbeddingDetails(scope.row)">
              查看详情
            </el-button>
            <el-button type="success" size="small" @click.stop="visualizeEmbedding(scope.row)">
              可视化
            </el-button>
            <el-button type="info" size="small" @click.stop="downloadEmbedding(scope.row.embedding_id)">
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 嵌入详情对话框 -->
    <el-dialog
      v-model="showEmbeddingDialog"
      title="嵌入详情"
      width="80%"
    >
      <div v-if="currentEmbedding" class="embedding-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文档名称">{{ currentEmbedding.filename }}</el-descriptions-item>
          <el-descriptions-item label="提供商">{{ currentEmbedding.provider_name }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ currentEmbedding.model_name }}</el-descriptions-item>
          <el-descriptions-item label="维度">{{ currentEmbedding.dimensions }}</el-descriptions-item>
          <el-descriptions-item label="向量数量">{{ currentEmbedding.vector_count }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTimestamp(currentEmbedding.timestamp) }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="embedding-samples">
          <h3>向量样本 (前10个)</h3>
          <el-collapse>
            <el-collapse-item v-for="(vector, i) in currentEmbedding.samples" :key="i" :title="`向量 ${i+1}`">
              <div class="vector-content">
                <pre>{{ JSON.stringify(vector, null, 2) }}</pre>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </el-dialog>
    
    <!-- 嵌入可视化对话框 -->
    <el-dialog
      v-model="showVisualizationDialog"
      title="嵌入向量可视化"
      width="80%"
      fullscreen
    >
      <div v-if="visualizationData" class="visualization-container">
        <div class="vis-controls">
          <el-select v-model="visualizationMethod" @change="updateVisualization" style="width: 150px">
            <el-option label="t-SNE" value="tsne" />
            <el-option label="UMAP" value="umap" />
            <el-option label="PCA" value="pca" />
          </el-select>
          <el-select v-model="visualizationDimensions" @change="updateVisualization" style="width: 150px">
            <el-option label="2D" :value="2" />
            <el-option label="3D" :value="3" />
          </el-select>
        </div>
        
        <div id="visualization-chart" class="visualization-chart"></div>
        
        <div class="hint">
          提示: 可视化展示了高维向量在低维空间的分布情况，相近的点表示语义相似的内容。
        </div>
      </div>
      <div v-else class="visualization-loading">
        <el-skeleton :rows="10" animated />
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useLoadingStore } from '../store/loading'
import { useEmbeddingStore } from '../store/embedding'
import { useChunkingStore } from '../store/chunking'
import { chunkingApi, embeddingApi } from '../services/api'
import { Document } from '@element-plus/icons-vue'

export default {
  name: 'VectorEmbedding',
  components: { Document },
  
  setup() {
    const loadingStore = useLoadingStore()
    const embeddingStore = useEmbeddingStore()
    const chunkingStore = useChunkingStore()
    
    // 状态
    const loading = ref(false)
    const processing = ref(false)
    const selectedFileId = ref('')
    const selectedProviderId = ref('')
    const selectedModelId = ref('')
    const showEmbeddingDialog = ref(false)
    const showVisualizationDialog = ref(false)
    const visualizationMethod = ref('tsne')
    const visualizationDimensions = ref(2)
    
    // 文件数据
    const jsonFiles = ref([])
    const selectedFile = ref(null)
    
    // 数据源
    const providers = ref([])
    const providerModels = ref([])
    const embeddings = ref([])
    const currentEmbedding = ref(null)
    const visualizationData = ref(null)
    
    // 计算属性
    const selectedModel = computed(() => {
      if (!selectedModelId.value) return null
      return providerModels.value.find(model => model.id === selectedModelId.value)
    })
    
    // 格式化时间戳
    const formatTimestamp = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleString()
    }
    
    // 加载JSON文件列表
    const fetchJsonFiles = async () => {
      loading.value = true
      try {
        await embeddingStore.fetchJsonFiles()
        jsonFiles.value = embeddingStore.jsonFiles
      } catch (error) {
        console.error('Error fetching JSON files:', error)
        jsonFiles.value = []
      } finally {
        loading.value = false
      }
    }
    
    // 加载嵌入提供商
    const fetchProviders = async () => {
      loading.value = true
      try {
        await embeddingStore.fetchProviders()
        providers.value = embeddingStore.providersList
      } catch (error) {
        console.error('Error fetching providers:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 当选择提供商时加载模型
    const onProviderChange = async (providerId) => {
      if (!providerId) return
      
      selectedModelId.value = ''
      loading.value = true
      
      try {
        await embeddingStore.fetchProviderModels(providerId)
        providerModels.value = embeddingStore.getModelsByProvider(providerId)
      } catch (error) {
        console.error('Error fetching provider models:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 当选择文件时加载嵌入历史和文件信息
    const onFileChange = async (fileId) => {
      if (!fileId) return
      
      loading.value = true
      embeddings.value = []
      selectedFile.value = null
      
      try {
        // 查找选中的文件信息
        selectedFile.value = jsonFiles.value.find(file => file.file_id === fileId) || null
        
        // 加载嵌入历史
        try {
          await embeddingStore.fetchEmbeddingHistory(fileId)
          embeddings.value = embeddingStore.getEmbeddingsByFileId(fileId) || []
        } catch (embeddingError) {
          console.error('Error fetching embedding history:', embeddingError)
          embeddings.value = []
        }
      } catch (error) {
        console.error('Error in onFileChange:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 创建嵌入
    const createEmbedding = async () => {
      if (!selectedFileId.value || !selectedProviderId.value || !selectedModelId.value) {
        ElMessage.warning('请选择文件、提供商和模型')
        return
      }
      
      processing.value = true
      try {
        await embeddingStore.createEmbeddings(
          selectedFileId.value, 
          selectedProviderId.value,
          selectedModelId.value
        )
        
        // 刷新嵌入历史
        await onFileChange(selectedFileId.value)
        
        ElMessage.success('嵌入创建成功')
      } catch (error) {
        console.error('Error creating embeddings:', error)
        ElMessage.error('创建嵌入失败: ' + (error.message || '未知错误'))
      } finally {
        processing.value = false
      }
    }
    
    // 查看嵌入详情
    const showEmbeddingDetails = async (row) => {
      loading.value = true
      try {
        await embeddingStore.fetchEmbeddingDetails(row.embedding_id)
        currentEmbedding.value = embeddingStore.currentEmbedding
        showEmbeddingDialog.value = true
      } catch (error) {
        console.error('Error fetching embedding details:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 可视化嵌入
    const visualizeEmbedding = async (row) => {
      loading.value = true
      visualizationData.value = null
      showVisualizationDialog.value = true
      
      try {
        await embeddingStore.fetchVisualizationData(
          row.embedding_id, 
          visualizationMethod.value, 
          visualizationDimensions.value
        )
        
        visualizationData.value = embeddingStore.getVisualizationData
        renderVisualization()
      } catch (error) {
        console.error('Error visualizing embedding:', error)
        ElMessage.error('嵌入可视化失败')
      } finally {
        loading.value = false
      }
    }
    
    // 更新可视化
    const updateVisualization = async () => {
      if (!currentEmbedding.value) return
      
      loading.value = true
      visualizationData.value = null
      
      try {
        await embeddingStore.fetchVisualizationData(
          currentEmbedding.value.embedding_id, 
          visualizationMethod.value, 
          visualizationDimensions.value
        )
        
        visualizationData.value = embeddingStore.getVisualizationData
        renderVisualization()
      } catch (error) {
        console.error('Error updating visualization:', error)
        ElMessage.error('更新可视化失败')
      } finally {
        loading.value = false
      }
    }
    
    // 渲染可视化图表
    const renderVisualization = () => {
      if (!visualizationData.value) return
      
      // 这里应该使用图表库（如ECharts）来渲染可视化
      // 作为示例，我们这里简单输出到控制台
      console.log('渲染可视化:', visualizationData.value)
      
      // 实际应用中，这里应该有调用图表库的代码
      // const chartDom = document.getElementById('visualization-chart')
      // const chart = echarts.init(chartDom)
      // chart.setOption({...})
    }
    
    // 下载嵌入结果
    const downloadEmbedding = (embeddingId) => {
      try {
        embeddingStore.downloadEmbedding(embeddingId)
        ElMessage.success('正在下载...')
      } catch (error) {
        console.error('Error downloading embedding:', error)
      }
    }
    
    onMounted(async () => {
      await fetchJsonFiles()
      await fetchProviders()
    })
    
    return {
      loading,
      processing,
      jsonFiles,
      selectedFileId,
      selectedFile,
      providers,
      selectedProviderId,
      providerModels,
      selectedModelId,
      selectedModel,
      embeddings,
      showEmbeddingDialog,
      currentEmbedding,
      showVisualizationDialog,
      visualizationMethod,
      visualizationDimensions,
      visualizationData,
      
      formatTimestamp,
      onProviderChange,
      onFileChange,
      createEmbedding,
      showEmbeddingDetails,
      visualizeEmbedding,
      updateVisualization,
      downloadEmbedding,
      
      Document
    }
  }
}
</script>

<style scoped>
.vector-embedding {
  padding: 20px;
}

h1, h2 {
  margin: 0 0 15px 0;
}

.select-document, .embedding-config, .embedding-history {
  margin-bottom: 20px;
}

.document-selector {
  margin-top: 15px;
}

.file-option {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.file-type {
  color: #909399;
  font-size: 0.9em;
}

.file-info {
  margin-top: 15px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.loading {
  padding: 20px 0;
}

.embedding-details {
  padding: 10px;
}

.embedding-samples {
  margin-top: 20px;
}

.vector-content pre {
  white-space: pre-wrap;
  font-size: 12px;
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}

.visualization-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.vis-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.visualization-chart {
  width: 100%;
  height: 500px;
  background-color: #f8f9fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.visualization-loading {
  padding: 20px;
}
</style> 