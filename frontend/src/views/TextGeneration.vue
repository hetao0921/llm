<template>
  <div class="text-generation">
    <h1>文本生成</h1>
    <p>基于检索的文本生成，支持多种生成策略。</p>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <!-- 生成区域 -->
        <el-card class="generation-area">
          <template #header>
            <div class="card-header">
              <span>生成内容</span>
              <div class="model-select">
                <el-select v-model="selectedModelId" placeholder="选择生成模型" size="small" style="width: 200px">
                  <el-option
                    v-for="model in generationModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                    :disabled="!model.available"
                  />
                </el-select>
              </div>
            </div>
          </template>
          
          <div class="prompt-area">
            <el-input
              v-model="prompt"
              type="textarea"
              :rows="4"
              placeholder="输入您的问题或提示..."
              resize="none"
            />
            <div class="prompt-actions">
              <el-checkbox v-model="useSearchResults">使用搜索结果增强生成</el-checkbox>
              <el-button type="primary" @click="generateText" :loading="generating" :disabled="!canGenerate">
                生成 <el-icon class="el-icon--right"><Document /></el-icon>
              </el-button>
            </div>
          </div>
          
          <div v-if="generating" class="generating-indicator">
            <el-skeleton :rows="10" animated />
          </div>
          
          <div v-else-if="generatedContent" class="generated-content">
            <div class="content-header">
              <h2>生成结果</h2>
              <div class="content-actions">
                <el-tooltip content="复制内容">
                  <el-button :icon="DocumentCopy" circle @click="copyContent" />
                </el-tooltip>
                <el-tooltip content="保存生成结果">
                  <el-button :icon="Star" circle @click="showSaveDialog = true" />
                </el-tooltip>
              </div>
            </div>
            
            <div class="content-body">
              <pre>{{ formattedContent }}</pre>
            </div>
            
            <div v-if="generatedContent.sources && generatedContent.sources.length > 0" class="sources">
              <h3>来源文档</h3>
              <el-collapse>
                <el-collapse-item v-for="(source, index) in generatedContent.sources" :key="index" :title="`来源 ${index + 1}`">
                  <div class="source-content">
                    <div>{{ source.text }}</div>
                    <div class="source-metadata" v-if="source.metadata">
                      <strong>元数据:</strong>
                      <pre>{{ JSON.stringify(source.metadata, null, 2) }}</pre>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
          
          <div v-else class="empty-content">
            <el-empty description="请输入提示并点击生成按钮" />
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <!-- 配置和历史 -->
        <el-card class="config-area">
          <template #header>
            <div class="card-header">
              <span>检索设置</span>
            </div>
          </template>
          
          <div v-if="useSearchResults" class="search-config">
            <el-form label-position="top">
              <!-- 选择索引 -->
              <el-form-item label="向量索引:">
                <el-select v-model="selectedIndexId" placeholder="选择向量索引" style="width: 100%">
                  <el-option
                    v-for="index in indices"
                    :key="index.id"
                    :label="`${index.name}`"
                    :value="index.id"
                  />
                </el-select>
              </el-form-item>
              
              <!-- 搜索配置 -->
              <el-form-item label="检索数量:">
                <el-input-number v-model="retrievalConfig.topK" :min="1" :max="20" size="small" />
              </el-form-item>
              
              <el-collapse>
                <el-collapse-item title="高级检索选项">
                  <el-form-item label="相关度阈值:">
                    <el-slider v-model="retrievalConfig.threshold" :min="0" :max="1" :step="0.05" />
                  </el-form-item>
                  
                  <el-form-item label="过滤条件:">
                    <el-input
                      v-model="retrievalConfig.filterJson"
                      type="textarea"
                      :rows="2"
                      placeholder="JSON格式过滤条件 (可选)"
                      size="small"
                    />
                  </el-form-item>
                </el-collapse-item>
              </el-collapse>
            </el-form>
          </div>
          <div v-else class="search-disabled">
            <el-empty description="检索增强已禁用" />
          </div>
        </el-card>
        
        <el-card class="history-area">
          <template #header>
            <div class="card-header">
              <span>生成历史</span>
              <el-button :icon="Refresh" circle size="small" @click="fetchGenerationHistory" :loading="loading" />
            </div>
          </template>
          
          <div v-if="loading" class="loading">
            <el-skeleton :rows="5" animated />
          </div>
          <div v-else-if="generationHistory.length === 0" class="no-history">
            <el-empty description="没有生成历史" />
          </div>
          <el-scrollbar height="300px">
            <div
              v-for="(item, index) in generationHistory"
              :key="index"
              class="history-item"
              @click="loadHistoryItem(item)"
            >
              <div class="history-prompt">{{ truncateText(item.prompt, 80) }}</div>
              <div class="history-meta">
                <span>{{ formatTimestamp(item.timestamp) }}</span>
                <span>{{ item.model_name }}</span>
              </div>
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 保存对话框 -->
    <el-dialog v-model="showSaveDialog" title="保存生成结果" width="30%">
      <el-form>
        <el-form-item label="标题">
          <el-input v-model="saveTitle" placeholder="请输入标题" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showSaveDialog = false">取消</el-button>
          <el-button type="primary" @click="saveGeneration" :loading="saving">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useGenerationStore } from '../store/generation'
import { useIndexingStore } from '../store/indexing'
import { Document, DocumentCopy, Star, Refresh } from '@element-plus/icons-vue'

export default {
  name: 'TextGeneration',
  components: { Document, DocumentCopy, Star, Refresh },
  
  setup() {
    const generationStore = useGenerationStore()
    const indexingStore = useIndexingStore()
    
    // 状态变量
    const loading = ref(false)
    const generating = ref(false)
    const saving = ref(false)
    const showSaveDialog = ref(false)
    
    // 数据源
    const generationModels = ref([])
    const indices = ref([])
    const generationHistory = ref([])
    
    // 表单数据
    const selectedModelId = ref('')
    const prompt = ref('')
    const useSearchResults = ref(false)
    const selectedIndexId = ref('')
    const retrievalConfig = ref({
      topK: 5,
      threshold: 0.7,
      filterJson: ''
    })
    const saveTitle = ref('')
    
    // 生成结果
    const generatedContent = ref(null)
    const currentGenerationId = ref(null)
    
    // 计算属性
    const canGenerate = computed(() => {
      return selectedModelId.value && prompt.value.trim() && 
        (!useSearchResults.value || selectedIndexId.value)
    })
    
    const formattedContent = computed(() => {
      if (!generatedContent.value || !generatedContent.value.text) return ''
      
      // 简单返回文本内容，不进行Markdown转换
      return generatedContent.value.text
    })
    
    // 初始化数据
    const initialize = async () => {
      loading.value = true
      try {
        await Promise.all([
          fetchGenerationModels(),
          fetchIndices(),
          fetchGenerationHistory()
        ])
      } catch (error) {
        console.error('Error initializing:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 获取生成模型
    const fetchGenerationModels = async () => {
      try {
        await generationStore.fetchGenerationModels()
        generationModels.value = generationStore.modelsList
        
        // 如果有可用模型，默认选择第一个
        if (generationModels.value.length > 0) {
          selectedModelId.value = generationModels.value[0].id
        }
      } catch (error) {
        console.error('Error fetching generation models:', error)
      }
    }
    
    // 获取索引列表
    const fetchIndices = async () => {
      try {
        await indexingStore.fetchIndices()
        indices.value = indexingStore.indicesList
        
        // 如果有可用索引，默认选择第一个
        if (indices.value.length > 0) {
          selectedIndexId.value = indices.value[0].id
        }
      } catch (error) {
        console.error('Error fetching indices:', error)
      }
    }
    
    // 获取生成历史
    const fetchGenerationHistory = async () => {
      try {
        await generationStore.fetchGenerationHistory()
        generationHistory.value = generationStore.historyList
      } catch (error) {
        console.error('Error fetching generation history:', error)
      }
    }
    
    // 生成文本
    const generateText = async () => {
      if (!canGenerate.value) return
      
      generating.value = true
      generatedContent.value = null
      currentGenerationId.value = null
      
      try {
        // 准备搜索结果（如果启用）
        let searchResults = []
        if (useSearchResults.value && selectedIndexId.value) {
          // 解析过滤条件
          let filter = {}
          try {
            if (retrievalConfig.value.filterJson) {
              filter = JSON.parse(retrievalConfig.value.filterJson)
            }
          } catch (e) {
            console.warn('Invalid filter JSON:', e)
          }
          
          // 执行搜索
          const results = await indexingStore.searchIndex(
            selectedIndexId.value,
            prompt.value,
            retrievalConfig.value.topK,
            filter
          )
          
          // 应用相关度阈值过滤
          searchResults = indexingStore.currentSearchResults
            .filter(result => result.score >= retrievalConfig.value.threshold)
        }
        
        // 生成文本
        const response = await generationStore.generateText(
          prompt.value,
          selectedModelId.value,
          searchResults,
          { includeSourceDetails: true }
        )
        
        generatedContent.value = response
        currentGenerationId.value = response.generation_id
        
      } catch (error) {
        console.error('Error generating text:', error)
        ElMessage.error('生成文本失败')
      } finally {
        generating.value = false
      }
    }
    
    // 保存生成结果
    const saveGeneration = async () => {
      if (!currentGenerationId.value || !saveTitle.value) {
        ElMessage.warning('请输入标题')
        return
      }
      
      saving.value = true
      try {
        await generationStore.saveGenerationResult(
          currentGenerationId.value,
          saveTitle.value
        )
        
        ElMessage.success('生成结果保存成功')
        showSaveDialog.value = false
        saveTitle.value = ''
        
        // 刷新历史
        await fetchGenerationHistory()
      } catch (error) {
        console.error('Error saving generation:', error)
        ElMessage.error('保存失败')
      } finally {
        saving.value = false
      }
    }
    
    // 复制内容到剪贴板
    const copyContent = () => {
      if (!generatedContent.value || !generatedContent.value.text) return
      
      navigator.clipboard.writeText(generatedContent.value.text)
        .then(() => ElMessage.success('内容已复制到剪贴板'))
        .catch(err => {
          console.error('Error copying to clipboard:', err)
          ElMessage.error('复制失败')
        })
    }
    
    // 加载历史记录
    const loadHistoryItem = async (item) => {
      loading.value = true
      try {
        await generationStore.fetchGenerationResult(item.generation_id)
        
        // 填充界面数据
        const result = generationStore.currentResult
        generatedContent.value = result
        currentGenerationId.value = result.generation_id
        prompt.value = result.prompt
        selectedModelId.value = result.model_id
        
        ElMessage.success('已加载历史生成结果')
      } catch (error) {
        console.error('Error loading history item:', error)
        ElMessage.error('加载历史记录失败')
      } finally {
        loading.value = false
      }
    }
    
    // 截断文本
    const truncateText = (text, maxLength) => {
      if (!text) return ''
      return text.length > maxLength ? text.slice(0, maxLength) + '...' : text
    }
    
    // 格式化时间戳
    const formatTimestamp = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleString()
    }
    
    onMounted(() => {
      initialize()
    })
    
    return {
      loading,
      generating,
      saving,
      showSaveDialog,
      generationModels,
      indices,
      generationHistory,
      selectedModelId,
      prompt,
      useSearchResults,
      selectedIndexId,
      retrievalConfig,
      saveTitle,
      generatedContent,
      currentGenerationId,
      canGenerate,
      formattedContent,
      
      fetchGenerationModels,
      fetchIndices,
      fetchGenerationHistory,
      generateText,
      saveGeneration,
      copyContent,
      loadHistoryItem,
      truncateText,
      formatTimestamp,
      
      Document,
      DocumentCopy,
      Star,
      Refresh
    }
  }
}
</script>

<style scoped>
.text-generation {
  padding: 20px;
}

h1 {
  margin: 0 0 15px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.generation-area {
  margin-bottom: 20px;
}

.config-area, .history-area {
  margin-bottom: 20px;
}

.prompt-area {
  margin-bottom: 20px;
}

.prompt-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.generating-indicator {
  padding: 20px 0;
}

.generated-content {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 15px;
  background-color: #f8f9fa;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.content-header h2 {
  margin: 0;
  font-size: 18px;
}

.content-actions {
  display: flex;
  gap: 10px;
}

.content-body {
  margin-bottom: 20px;
  line-height: 1.6;
}

.content-body pre {
  white-space: pre-wrap;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  background-color: transparent;
  padding: 0;
  margin: 0;
}

.sources {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.sources h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 16px;
  color: #606266;
}

.source-content {
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.source-metadata {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e0e0e0;
}

.source-metadata pre {
  white-space: pre-wrap;
  font-size: 12px;
  margin-top: 5px;
}

.search-disabled, .empty-content, .no-history {
  padding: 30px 0;
  text-align: center;
}

.history-item {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
}

.history-item:hover {
  background-color: #f5f7fa;
}

.history-prompt {
  font-size: 14px;
  line-height: 1.4;
  margin-bottom: 5px;
}

.history-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  justify-content: space-between;
}

.loading {
  padding: 10px;
}
</style> 