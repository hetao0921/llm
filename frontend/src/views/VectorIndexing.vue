<template>
  <div class="vector-indexing">
    <h1>向量索引</h1>
    <p>构建和管理向量索引，支持高效的相似度搜索。</p>
    
    <el-card class="main-content">
      <template #header>
        <div class="card-header">
          <span>索引管理</span>
        </div>
      </template>
      
      <el-tabs v-model="activeTab">
        <!-- 创建索引面板 -->
        <el-tab-pane label="创建索引" name="create">
          <div class="create-index">
            <h2>选择嵌入数据源</h2>
            <div v-if="loading" class="loading">
              <el-skeleton :rows="3" animated />
            </div>
            
            <el-form label-position="top">
              <!-- 选择嵌入数据 -->
              <el-form-item label="选择嵌入数据:">
                <el-select v-model="selectedEmbeddingId" placeholder="选择已创建的嵌入数据" style="width: 100%">
                  <el-option
                    v-for="embedding in availableEmbeddings"
                    :key="embedding.embedding_id"
                    :label="`${embedding.filename} (${embedding.provider_name}:${embedding.model_name})`"
                    :value="embedding.embedding_id"
                  />
                </el-select>
              </el-form-item>
              
              <!-- 选择向量数据库类型 -->
              <el-form-item label="向量数据库:">
                <el-select v-model="selectedDbType" placeholder="选择向量数据库" style="width: 100%" @change="onDbTypeChange">
                  <el-option
                    v-for="db in vectorDatabases"
                    :key="db.id"
                    :label="db.name"
                    :value="db.id"
                    :disabled="!db.available"
                  />
                </el-select>
                <div class="hint" v-if="selectedDbInfo">
                  {{ selectedDbInfo.description }}
                </div>
              </el-form-item>
              
              <!-- 索引名称 -->
              <el-form-item label="索引名称:">
                <el-input v-model="indexName" placeholder="请输入索引名称"></el-input>
              </el-form-item>
              
              <!-- 数据库特定配置 -->
              <template v-if="selectedDbType === 'milvus'">
                <el-form-item label="集合参数:">
                  <el-input-number v-model="milvusConfig.dim" :min="1" :max="2048" label="向量维度"></el-input-number>
                  <el-select v-model="milvusConfig.metric_type" placeholder="距离度量">
                    <el-option label="欧氏距离" value="L2" />
                    <el-option label="内积" value="IP" />
                    <el-option label="余弦相似度" value="COSINE" />
                  </el-select>
                </el-form-item>
              </template>
              
              <template v-else-if="selectedDbType === 'pinecone'">
                <el-form-item label="Pinecone环境:">
                  <el-input v-model="pineconeConfig.environment" placeholder="Pinecone环境"></el-input>
                </el-form-item>
              </template>
              
              <!-- 创建索引按钮 -->
              <el-form-item>
                <el-button type="primary" @click="createIndex" :loading="processing">创建索引</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
        
        <!-- 索引列表面板 -->
        <el-tab-pane label="索引列表" name="list">
          <div class="indices-list">
            <div class="controls">
              <el-button type="primary" @click="fetchIndices" size="small" :loading="loading">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
            
            <div v-if="loading" class="loading">
              <el-skeleton :rows="5" animated />
            </div>
            <div v-else-if="indices.length === 0" class="no-indices">
              <el-empty description="没有可用的索引" />
            </div>
            <el-table v-else :data="indices" style="width: 100%">
              <el-table-column label="索引名称" prop="name" />
              <el-table-column label="数据库类型" prop="db_type" />
              <el-table-column label="向量数量" prop="vector_count" />
              <el-table-column label="创建时间">
                <template #default="scope">
                  {{ formatTimestamp(scope.row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作">
                <template #default="scope">
                  <el-button type="primary" size="small" @click="viewIndexDetails(scope.row)">详情</el-button>
                  <el-button type="danger" size="small" @click="confirmDeleteIndex(scope.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <!-- 向量搜索面板 -->
        <el-tab-pane label="向量搜索" name="search">
          <div class="vector-search">
            <!-- 选择索引 -->
            <el-form label-position="top">
              <el-form-item label="选择索引:">
                <el-select v-model="selectedIndexId" placeholder="选择向量索引" style="width: 100%">
                  <el-option
                    v-for="index in indices"
                    :key="index.id"
                    :label="`${index.name} (${index.db_type})`"
                    :value="index.id"
                  />
                </el-select>
              </el-form-item>
              
              <!-- 搜索查询 -->
              <el-form-item label="搜索查询:">
                <el-input
                  v-model="searchQuery"
                  type="textarea"
                  :rows="3"
                  placeholder="输入查询文本，系统会将其转换为向量进行相似度匹配"
                ></el-input>
              </el-form-item>
              
              <!-- 搜索参数 -->
              <el-form-item label="返回结果数量:">
                <el-input-number v-model="topK" :min="1" :max="100"></el-input-number>
              </el-form-item>
              
              <!-- 高级过滤选项 -->
              <el-collapse>
                <el-collapse-item title="高级过滤选项">
                  <el-form-item label="元数据过滤:">
                    <el-input
                      v-model="filterJson"
                      type="textarea"
                      :rows="2"
                      placeholder="输入JSON格式的过滤条件 (可选)"
                    ></el-input>
                    <div class="hint">例如: {"category": "science", "confidence": {"$gt": 0.8}}</div>
                  </el-form-item>
                </el-collapse-item>
              </el-collapse>
              
              <!-- 搜索按钮 -->
              <el-form-item>
                <el-button type="primary" @click="searchIndex" :loading="searching">
                  <el-icon><Search /></el-icon> 搜索
                </el-button>
              </el-form-item>
            </el-form>
            
            <!-- 搜索结果 -->
            <div v-if="searchResults.length > 0" class="search-results">
              <h2>搜索结果</h2>
              <el-table :data="searchResults" style="width: 100%">
                <el-table-column label="相关度得分" width="100">
                  <template #default="scope">
                    <el-progress :percentage="Math.round(scope.row.score * 100)" :format="format => `${format}%`" />
                  </template>
                </el-table-column>
                <el-table-column label="内容">
                  <template #default="scope">
                    <div class="result-content">{{ scope.row.text }}</div>
                    <div class="result-metadata" v-if="scope.row.metadata">
                      <el-collapse>
                        <el-collapse-item title="元数据">
                          <pre>{{ JSON.stringify(scope.row.metadata, null, 2) }}</pre>
                        </el-collapse-item>
                      </el-collapse>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
              
              <!-- 保存搜索结果 -->
              <div class="save-results">
                <el-button type="success" @click="saveSearchResults" :disabled="!currentSearchId">
                  <el-icon><Download /></el-icon> 保存搜索结果
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>
        
        <!-- 搜索历史面板 -->
        <el-tab-pane label="搜索历史" name="history">
          <div class="search-history">
            <div class="controls">
              <el-button type="primary" @click="fetchSearchHistory" size="small" :loading="loading">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
            
            <div v-if="loading" class="loading">
              <el-skeleton :rows="5" animated />
            </div>
            <div v-else-if="searchHistory.length === 0" class="no-history">
              <el-empty description="没有搜索历史" />
            </div>
            <el-table v-else :data="searchHistory" style="width: 100%">
              <el-table-column label="搜索时间">
                <template #default="scope">
                  {{ formatTimestamp(scope.row.timestamp) }}
                </template>
              </el-table-column>
              <el-table-column label="索引名称" prop="index_name" />
              <el-table-column label="查询文本" prop="query" />
              <el-table-column label="结果数量" prop="result_count" />
              <el-table-column label="操作">
                <template #default="scope">
                  <el-button type="primary" size="small" @click="viewSearchResults(scope.row)">查看结果</el-button>
                </template>
              </el-table-column>
            </el-table>
      </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 索引详情对话框 -->
    <el-dialog
      v-model="showIndexDialog"
      title="索引详情"
      width="80%"
    >
      <div v-if="currentIndex" class="index-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="索引名称">{{ currentIndex.name }}</el-descriptions-item>
          <el-descriptions-item label="数据库类型">{{ currentIndex.db_type }}</el-descriptions-item>
          <el-descriptions-item label="向量数量">{{ currentIndex.vector_count }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTimestamp(currentIndex.created_at) }}</el-descriptions-item>
        </el-descriptions>
        
        <div class="index-config">
          <h3>索引配置</h3>
          <pre>{{ JSON.stringify(currentIndex.config, null, 2) }}</pre>
        </div>
        
        <div class="source-info">
          <h3>数据源信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="嵌入ID">{{ currentIndex.embedding_id }}</el-descriptions-item>
            <el-descriptions-item label="嵌入提供商">{{ currentIndex.provider_name }}</el-descriptions-item>
            <el-descriptions-item label="嵌入模型">{{ currentIndex.model_name }}</el-descriptions-item>
            <el-descriptions-item label="维度">{{ currentIndex.dimensions }}</el-descriptions-item>
            <el-descriptions-item label="源文件名">{{ currentIndex.filename }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useIndexingStore } from '../store/indexing'
import { useEmbeddingStore } from '../store/embedding'
import { Refresh, Search, Download } from '@element-plus/icons-vue'

export default {
  name: 'VectorIndexing',
  components: { Refresh, Search, Download },
  
  setup() {
    const indexingStore = useIndexingStore()
    const embeddingStore = useEmbeddingStore()
    
    // 标签页
    const activeTab = ref('create')
    
    // 状态
    const loading = ref(false)
    const processing = ref(false)
    const searching = ref(false)
    const showIndexDialog = ref(false)
    
    // 创建索引数据
    const availableEmbeddings = ref([])
    const vectorDatabases = ref([])
    const selectedEmbeddingId = ref('')
    const selectedDbType = ref('')
    const indexName = ref('')
    const milvusConfig = ref({ dim: 128, metric_type: 'L2' })
    const pineconeConfig = ref({ environment: 'us-west1-gcp' })
    
    // 索引列表数据
    const indices = ref([])
    const currentIndex = ref(null)
    
    // 搜索数据
    const selectedIndexId = ref('')
    const searchQuery = ref('')
    const topK = ref(5)
    const filterJson = ref('')
    const searchResults = ref([])
    const currentSearchId = ref(null)
    
    // 搜索历史
    const searchHistory = ref([])
    
    // 计算属性
    const selectedDbInfo = computed(() => {
      if (!selectedDbType.value) return null
      return vectorDatabases.value.find(db => db.id === selectedDbType.value)
    })
    
    // 加载嵌入数据
    const fetchEmbeddings = async () => {
      loading.value = true
      try {
        // 实际应用中，应该调用API获取所有嵌入数据
        // 这里简化处理，模拟一些数据
        availableEmbeddings.value = [
          {
            embedding_id: 'emb-001',
            filename: '大模型介绍.pdf',
            provider_name: 'OpenAI',
            model_name: 'text-embedding-ada-002',
            dimensions: 1536
          },
          {
            embedding_id: 'emb-002',
            filename: '数据分析报告.pdf',
            provider_name: 'HuggingFace',
            model_name: 'sentence-transformers/all-MiniLM-L6-v2',
            dimensions: 384
          }
        ]
      } catch (error) {
        console.error('Error fetching embeddings:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 加载向量数据库列表
    const fetchVectorDatabases = async () => {
      loading.value = true
      try {
        await indexingStore.fetchVectorDatabases()
        vectorDatabases.value = indexingStore.databasesList
      } catch (error) {
        console.error('Error fetching vector databases:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 加载索引列表
    const fetchIndices = async () => {
      loading.value = true
      try {
        await indexingStore.fetchIndices()
        indices.value = indexingStore.indicesList
      } catch (error) {
        console.error('Error fetching indices:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 加载搜索历史
    const fetchSearchHistory = async () => {
      loading.value = true
      try {
        await indexingStore.fetchSearchHistory()
        searchHistory.value = indexingStore.searchHistoryList
      } catch (error) {
        console.error('Error fetching search history:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 数据库类型变更事件
    const onDbTypeChange = (dbType) => {
      // 根据数据库类型加载相应的配置项
      console.log('选择数据库类型:', dbType)
    }
    
    // 创建索引
    const createIndex = async () => {
      if (!selectedEmbeddingId.value || !selectedDbType.value || !indexName.value) {
        ElMessage.warning('请填写完整的索引信息')
        return
      }
      
      processing.value = true
      try {
        // 根据数据库类型获取配置
        let config = {}
        if (selectedDbType.value === 'milvus') {
          config = milvusConfig.value
        } else if (selectedDbType.value === 'pinecone') {
          config = pineconeConfig.value
        }
        
        await indexingStore.createIndex(
          selectedEmbeddingId.value,
          selectedDbType.value,
          indexName.value,
          config
        )
        
        ElMessage.success('索引创建成功')
        activeTab.value = 'list'  // 切换到索引列表
      } catch (error) {
        console.error('Error creating index:', error)
      } finally {
        processing.value = false
      }
    }
    
    // 查看索引详情
    const viewIndexDetails = async (index) => {
      loading.value = true
      try {
        await indexingStore.fetchIndexDetails(index.id)
        currentIndex.value = indexingStore.currentIndex
        showIndexDialog.value = true
      } catch (error) {
        console.error('Error fetching index details:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 确认删除索引
    const confirmDeleteIndex = (index) => {
      ElMessageBox.confirm(
        `确认删除索引 "${index.name}"？此操作不可逆。`,
        '删除确认',
        {
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
        .then(() => {
          deleteIndex(index.id)
        })
        .catch(() => {
          // 用户取消删除
        })
    }
    
    // 删除索引
    const deleteIndex = async (indexId) => {
      processing.value = true
      try {
        await indexingStore.deleteIndex(indexId)
        ElMessage.success('索引删除成功')
      } catch (error) {
        console.error('Error deleting index:', error)
      } finally {
        processing.value = false
      }
    }
    
    // 搜索索引
    const searchIndex = async () => {
      if (!selectedIndexId.value || !searchQuery.value) {
        ElMessage.warning('请选择索引并输入查询内容')
        return
      }
      
      searching.value = true
      try {
        let filter = {}
        if (filterJson.value) {
          try {
            filter = JSON.parse(filterJson.value)
          } catch (e) {
            ElMessage.warning('过滤条件JSON格式无效，将忽略过滤')
          }
        }
        
        const results = await indexingStore.searchIndex(
          selectedIndexId.value,
          searchQuery.value,
          topK.value,
          filter
        )
        
        searchResults.value = indexingStore.currentSearchResults
        currentSearchId.value = results.search_id
        
        if (searchResults.value.length === 0) {
          ElMessage.info('没有找到匹配的结果')
        }
      } catch (error) {
        console.error('Error searching index:', error)
      } finally {
        searching.value = false
      }
    }
    
    // 保存搜索结果
    const saveSearchResults = async () => {
      if (!currentSearchId.value) return
      
      processing.value = true
      try {
        await indexingStore.saveSearchResult(currentSearchId.value)
        ElMessage.success('搜索结果已保存')
      } catch (error) {
        console.error('Error saving search results:', error)
      } finally {
        processing.value = false
      }
    }
    
    // 查看历史搜索结果
    const viewSearchResults = (searchItem) => {
      // 在实际应用中，应该通过API加载搜索结果详情
      ElMessage.info('正在加载搜索结果，此功能尚未实现')
    }
    
    // 格式化时间戳
    const formatTimestamp = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleString()
    }
    
    onMounted(async () => {
      // 初始化数据
      await Promise.all([
        fetchEmbeddings(),
        fetchVectorDatabases(),
        fetchIndices()
      ])
    })
    
    return {
      activeTab,
      loading,
      processing,
      searching,
      
      // 创建索引
      availableEmbeddings,
      vectorDatabases,
      selectedEmbeddingId,
      selectedDbType,
      selectedDbInfo,
      indexName,
      milvusConfig,
      pineconeConfig,
      
      // 索引列表
      indices,
      currentIndex,
      showIndexDialog,
      
      // 搜索
      selectedIndexId,
      searchQuery,
      topK,
      filterJson,
      searchResults,
      currentSearchId,
      
      // 搜索历史
      searchHistory,
      
      // 方法
      onDbTypeChange,
      createIndex,
      fetchIndices,
      viewIndexDetails,
      confirmDeleteIndex,
      searchIndex,
      saveSearchResults,
      fetchSearchHistory,
      viewSearchResults,
      formatTimestamp
    }
  }
}
</script>

<style scoped>
.vector-indexing {
  padding: 20px;
}

.main-content {
  margin-top: 20px;
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

.controls {
  margin-bottom: 15px;
}

.search-results {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.result-content {
  margin-bottom: 10px;
}

.result-metadata pre {
  white-space: pre-wrap;
  font-size: 12px;
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
}

.save-results {
  margin-top: 20px;
  text-align: right;
}

.index-details {
  padding: 10px;
}

.index-config, .source-info {
  margin-top: 20px;
}

.index-config pre {
  white-space: pre-wrap;
  font-size: 12px;
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
}

.no-indices, .no-history {
  padding: 40px 0;
  text-align: center;
}
</style> 