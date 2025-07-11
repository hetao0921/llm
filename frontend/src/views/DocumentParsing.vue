<template>
  <div class="document-parsing">
    <h1>文档解析</h1>
    <p>解析文档内容，提取关键信息和结构化数据。</p>
    
    <div class="select-document">
      <h2>1. 选择文档</h2>
      <div v-if="loading" class="loading">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="files.length === 0">
        <el-alert
          title="没有可用的文档"
          description="请先在文件加载页面上传文档"
          type="info"
          :closable="false"
          show-icon
        />
      </div>
      <div v-else class="document-selector">
        <el-select v-model="selectedFileId" placeholder="选择一个文档" style="width: 100%" @change="onFileChange">
          <el-option
            v-for="file in files"
            :key="file.file_id"
            :label="file.filename"
            :value="file.file_id"
          />
        </el-select>
      </div>
    </div>
    
    <el-card v-if="selectedFileId" class="parsing-config">
      <template #header>
        <div class="card-header">
          <span><h2>2. 配置解析策略</h2></span>
        </div>
      </template>
      
      <!-- 解析策略选择 -->
      <div class="strategy-select">
        <el-form label-position="top">
          <el-form-item label="解析策略:">
            <el-select v-model="parsingMethod" placeholder="选择策略" style="width: 100%">
              <el-option 
                v-for="(method, key) in availableMethods"
                :key="key"
                :label="method.name"
                :value="key"
                :disabled="!method.supported"
              />
            </el-select>
          </el-form-item>
          
          <!-- 策略说明 -->
          <el-alert
            v-if="selectedMethod && selectedMethod.description"
            :title="selectedMethod.name"
            :description="selectedMethod.description"
            type="info"
            :closable="false"
          />
          
          <!-- 表格选项 -->
          <el-form-item v-if="parsingMethod === 'text_and_tables'">
            <el-checkbox v-model="includeTables">包含表格</el-checkbox>
            <div class="hint">启用后，将尝试提取文档中的表格</div>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="processParsing" :loading="processing">
              开始解析
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    
    <!-- 解析历史 -->
    <el-card v-if="selectedFileId && parsingHistory.length > 0" class="parsing-history">
      <template #header>
        <div class="card-header">
          <span><h2>解析历史</h2></span>
        </div>
      </template>
      
      <el-table :data="parsingHistory" style="width: 100%" @row-click="showParsingResult">
        <el-table-column label="解析时间" width="180">
          <template #default="scope">
            {{ formatTimestamp(scope.row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column label="解析策略" width="150">
          <template #default="scope">
            {{ scope.row.method_name }}
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="scope">
            <el-button type="primary" size="small" @click.stop="showParsingResult(scope.row)">
              查看结果
            </el-button>
            <el-dropdown @command="(cmd) => downloadResult(scope.row.parsing_id, cmd)">
              <el-button type="success" size="small">
                下载 <el-icon><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="json">JSON格式</el-dropdown-item>
                  <el-dropdown-item command="txt">纯文本格式</el-dropdown-item>
                  <el-dropdown-item command="html">HTML格式</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 解析结果显示 -->
    <el-card v-if="currentResult" class="parsing-result">
      <template #header>
        <div class="card-header">
          <h2>解析结果: {{ currentResult.method_name }}</h2>
          <div class="result-actions">
            <el-dropdown @command="(cmd) => downloadResult(currentResult.parsing_id, cmd)">
              <el-button type="success" size="small">
                下载 <el-icon><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="json">JSON格式</el-dropdown-item>
                  <el-dropdown-item command="txt">纯文本格式</el-dropdown-item>
                  <el-dropdown-item command="html">HTML格式</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>
      
      <!-- 根据解析方法不同显示不同内容 -->
      <div v-if="currentResult.parse_method === 'full_text'" class="content-view">
        <h3>全文内容</h3>
        <div class="text-content">
          <pre>{{ currentResult.content?.full_text }}</pre>
        </div>
      </div>
      
      <div v-else-if="currentResult.parse_method === 'by_page'" class="content-view">
        <h3>分页内容</h3>
        <el-tabs type="border-card">
          <el-tab-pane 
            v-for="(text, pageNum) in currentResult.content?.pages" 
            :key="pageNum"
            :label="`第 ${parseInt(pageNum) + 1} 页`"
          >
            <div class="text-content">
              <pre>{{ text }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      
      <div v-else-if="currentResult.parse_method === 'by_heading'" class="content-view">
        <h3>按标题解析内容</h3>
        <el-collapse>
          <el-collapse-item
            v-for="(content, heading, index) in currentResult.content?.sections"
            :key="index"
            :title="heading"
          >
            <div class="text-content">
              <pre>{{ content }}</pre>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
      
      <div v-else-if="currentResult.parse_method === 'tables_only'" class="content-view">
        <h3>表格内容</h3>
        <div v-if="!currentResult.content?.tables || currentResult.content.tables.length === 0" class="no-tables">
          <el-empty description="未找到表格" />
        </div>
        <div v-else class="tables-view">
          <el-tabs type="border-card">
            <el-tab-pane 
              v-for="(table, index) in currentResult.content.tables" 
              :key="index"
              :label="`表格 ${index + 1}`"
            >
              <div class="html-content" v-html="table.html"></div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
      
      <div v-else-if="currentResult.parse_method === 'text_and_tables'" class="content-view">
        <el-tabs type="border-card">
          <el-tab-pane label="文本内容">
            <div class="text-content">
              <pre>{{ currentResult.content?.full_text }}</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="表格内容" v-if="currentResult.include_tables">
            <div v-if="!currentResult.content?.tables || currentResult.content.tables.length === 0" class="no-tables">
              <el-empty description="未找到表格" />
            </div>
            <div v-else class="tables-view">
              <el-tabs type="card">
                <el-tab-pane 
                  v-for="(table, index) in currentResult.content.tables" 
                  :key="index"
                  :label="`表格 ${index + 1}`"
                >
                  <div class="html-content" v-html="table.html"></div>
                </el-tab-pane>
              </el-tabs>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useLoadingStore } from '../store/loading'
import { useParsingStore } from '../store/parsing'
import { ArrowDown } from '@element-plus/icons-vue'

export default {
  name: 'DocumentParsing',
  components: {
    ArrowDown
  },
  setup() {
    const loadingStore = useLoadingStore()
    const parsingStore = useParsingStore()

    const loading = ref(false)
    const processing = ref(false)
    const selectedFileId = ref('')
    const parsingMethod = ref('full_text')
    const includeTables = ref(false)
    const files = ref([])

    // 计算属性
    const availableMethods = computed(() => {
      if (!selectedFileId.value) return {}
      return parsingStore.getMethodsByFileId(selectedFileId.value) || {}
    })
    
    const selectedMethod = computed(() => {
      if (!parsingMethod.value || !availableMethods.value) return null
      return availableMethods.value[parsingMethod.value] || null
    })

    const parsingHistory = computed(() => {
      if (!selectedFileId.value) return []
      return parsingStore.getHistoryByFileId(selectedFileId.value) || []
    })

    const currentResult = computed(() => {
      return parsingStore.currentResult
    })

    // 加载文件列表
    const loadFiles = async () => {
      loading.value = true
      try {
        await loadingStore.fetchFiles()
        files.value = loadingStore.files
      } catch (error) {
        console.error('Error fetching files:', error)
        ElMessage.error('加载文件列表失败')
      } finally {
        loading.value = false
      }
    }

    // 文件变更时加载可用解析方法
    const onFileChange = async () => {
      if (!selectedFileId.value) return

      loading.value = true
      try {
        await parsingStore.getAvailableMethods(selectedFileId.value)
        
        // 默认选择第一个可用方法
        const methods = availableMethods.value
        for (const key in methods) {
          if (methods[key].supported) {
            parsingMethod.value = key
            break
          }
        }
        
        // 加载解析历史
        await parsingStore.getParsingHistory(selectedFileId.value)
        
        // 如果有历史记录，默认显示最新一条
        if (parsingHistory.value.length > 0) {
          await showParsingResult(parsingHistory.value[0])
        } else {
          parsingStore.clearResult()
        }
      } catch (error) {
        console.error('Error loading parsing methods:', error)
        ElMessage.error('加载解析方法失败')
      } finally {
        loading.value = false
      }
    }

    // 执行解析
    const processParsing = async () => {
      if (!selectedFileId.value) return
      
      processing.value = true
      try {
        await parsingStore.parseDocument(
          selectedFileId.value,
          parsingMethod.value,
          includeTables.value
        )
        
        ElMessage.success('文档解析成功')
      } catch (error) {
        console.error('Error during parsing:', error)
        ElMessage.error('文档解析失败')
      } finally {
        processing.value = false
      }
    }

    // 显示解析结果
    const showParsingResult = async (row) => {
      if (!row || !row.parsing_id) return
      
      loading.value = true
      try {
        await parsingStore.getParsingResult(row.parsing_id)
      } catch (error) {
        console.error('Error fetching parsing result:', error)
        ElMessage.error('加载解析结果失败')
      } finally {
        loading.value = false
      }
    }

    // 下载解析结果
    const downloadResult = (parsingId, format) => {
      try {
        parsingStore.downloadResult(parsingId, format)
        ElMessage.success(`正在下载${format}格式文件...`)
      } catch (error) {
        console.error('Error downloading result:', error)
        ElMessage.error('下载解析结果失败')
      }
    }

    // 格式化时间戳
    const formatTimestamp = (timestamp) => {
      if (!timestamp) return '未知时间'
      
      // 格式: 20240521134523 -> 2024-05-21 13:45:23
      const year = timestamp.substring(0, 4)
      const month = timestamp.substring(4, 6)
      const day = timestamp.substring(6, 8)
      const hour = timestamp.substring(8, 10)
      const minute = timestamp.substring(10, 12)
      const second = timestamp.substring(12, 14)
      
      return `${year}-${month}-${day} ${hour}:${minute}:${second}`
    }

    onMounted(async () => {
      await loadFiles()
    })

    return {
      loading,
      processing,
      selectedFileId,
      parsingMethod,
      includeTables,
      files,
      availableMethods,
      selectedMethod,
      parsingHistory,
      currentResult,
      onFileChange,
      processParsing,
      showParsingResult,
      downloadResult,
      formatTimestamp,
      ArrowDown
    }
  }
}
</script>

<style scoped>
.document-parsing {
  padding: 20px;
}

h1, h2, h3 {
  margin: 0 0 15px 0;
}

.select-document, .parsing-config, .parsing-history, .parsing-result {
  margin-bottom: 20px;
}

.document-selector {
  margin-top: 15px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.loading {
  padding: 20px 0;
}

.text-content {
  max-height: 500px;
  overflow-y: auto;
}

.text-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: monospace;
  line-height: 1.5;
  font-size: 14px;
  padding: 10px;
  background-color: #f8f8f8;
  border-radius: 4px;
}

.html-content {
  overflow-x: auto;
}

.html-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.html-content :deep(th),
.html-content :deep(td) {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.html-content :deep(tr:nth-child(even)) {
  background-color: #f2f2f2;
}

.html-content :deep(th) {
  padding-top: 12px;
  padding-bottom: 12px;
  text-align: left;
  background-color: #4CAF50;
  color: white;
}

.result-actions {
  display: flex;
  gap: 10px;
}

.content-view {
  margin-top: 20px;
}

.no-tables {
  padding: 30px 0;
}
</style> 