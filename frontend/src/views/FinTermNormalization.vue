<template>
  <div class="fin-term-normalization">
    <h1>金融术语标准化</h1>
    <p>在此页面对金融术语进行标准化处理。</p>

    <div class="content">
      <!-- 输入框 -->
      <div class="input-section">
        <h2>输入文本</h2>
        <el-input 
          type="textarea" 
          v-model="inputText" 
          :rows="6" 
          placeholder="请输入需要进行标准化的文本" 
        />
      </div>
      
      <!-- 模型选择 -->
      <div class="model-section">
        <h2>模型选择</h2>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="嵌入式模型供应商">
              <el-select v-model="modelProvider" placeholder="选择模型供应商" style="width: 100%">
                <el-option label="siliconflow" value="siliconflow" />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="12">
            <el-form-item label="嵌入式模型名称">
              <el-select v-model="modelName" placeholder="选择模型名称" style="width: 100%">
                <el-option label="BAAI/bge-m3（默认）" value="BAAI/bge-m3" />
                <el-option label="BAAI/bge-small-zh-v1.5" value="BAAI/bge-small-zh-v1.5" />
                <el-option label="netease-youdao/bce-embedding-base_v1" value="netease-youdao/bce-embedding-base_v1" />
                <el-option label="BAAI/bge-large-zh-v1.5" value="BAAI/bge-large-zh-v1.5" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </div>
      
      <!-- 向量数据库选择 -->
      <div class="db-section">
        <h2>向量数据库配置</h2>
        
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="向量数据库类型">
              <el-select v-model="dbType" placeholder="选择数据库类型" style="width: 100%" @change="handleDbTypeChange">
                <el-option label="ChromaDB" value="chromadb" />
                <el-option label="Milvus" value="milvus" />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="8" v-if="dbType === 'chromadb'">
            <el-form-item label="索引类型">
              <el-select v-model="indexType" placeholder="选择索引类型" style="width: 100%">
                <el-option label="HNSW（分层可导航小世界图）" value="hnsw" />
                <el-option label="ANNOY（基于树的分区结构）" value="annoy" />
                <el-option label="FLAT（无索引）" value="flat" />
              </el-select>
            </el-form-item>
          </el-col>
          
          <el-col :span="8">
            <el-form-item label="集合名称">
              <el-select v-model="collectionName" placeholder="选择集合名称" style="width: 100%">
                <el-option label="my_finterm_collection" value="my_finterm_collection" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- 术语分类选择 -->
      <div class="classification-section">
        <h2>术语分类</h2>
        <p>请选择需要处理的术语类型（可单选和多选）</p>
        
        <div class="classification-options">
          <!-- 全选选项 -->
          <div class="select-all-option">
            <el-checkbox 
              v-model="selectAllClasses" 
              @change="handleSelectAllClassesChange"
              :indeterminate="isClassIndeterminate"
              label="全选"
            >
              全选
            </el-checkbox>
            <span v-if="selectedClassifications.length > 0" class="selection-info">
              已选 {{ selectedClassifications.length }}/{{ classifications.length }} 项
            </span>
          </div>
          
          <el-divider />
          
          <el-checkbox-group v-model="selectedClassifications" @change="handleClassificationsChange">
            <el-row :gutter="20">
              <el-col :span="8" v-for="classification in classifications" :key="classification.code">
                <el-checkbox :label="classification.code" :key="classification.code">
                  <div class="classification-item">
                    <span class="code">{{ classification.code }}</span>
                    <span class="name">{{ classification.description }} ({{ classification.name }})</span>
                    <el-tooltip :content="`${classification.description} - ${classification.name}`" placement="top">
                      <el-icon><InfoFilled /></el-icon>
                    </el-tooltip>
                  </div>
                </el-checkbox>
              </el-col>
            </el-row>
          </el-checkbox-group>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button type="primary" :loading="loading" @click="performNormalization">术语标准化</el-button>
      </div>

      <!-- 加载中提示 -->
      <div class="json-result" v-if="loading">
        <el-card shadow="hover" class="json-card">
          <div class="loading-container">
            <el-skeleton :rows="6" animated />
            <div class="loading-text">正在处理，请稍候...</div>
          </div>
        </el-card>
      </div>

      <!-- JSON结果展示 - 直接放在按钮下方，使用showResults而非hasResults -->
      <div class="json-result" v-if="showResults && !loading">
        <el-card shadow="hover" class="json-card">
          <template #header>
            <div class="card-header">
              <span>返回结果</span>
              <el-button type="primary" size="small" plain @click="copyToClipboard(JSON.stringify(normalizationResults, null, 2))">
                复制JSON
              </el-button>
            </div>
          </template>
          <div class="json-content" v-html="highlightJson(JSON.stringify(normalizationResults))"></div>
        </el-card>
      </div>

      <!-- 结果说明 -->
      <div class="result-info" v-if="!showResults && !loading">
        <el-alert
          title="请点击&quot;术语标准化&quot;按钮进行处理"
          type="info"
          description="处理完成后，将在此处显示返回的JSON结果"
          show-icon
          :closable="false"
        />
      </div>

      <!-- 结果展示 - 只在有实体详情时显示 -->
      <div class="results-section" v-if="normalizationResults.实体详情?.length > 0">
        <h2>标准化结果</h2>
        
        <!-- 实体详情表格 -->
        <div class="entity-details">
          <h3>识别出的金融实体</h3>
          <el-table :data="normalizationResults.实体详情" style="width: 100%" border>
            <el-table-column prop="识别实体" label="识别实体" />
            <el-table-column prop="实体分类" label="实体分类">
              <template #default="scope">
                <el-tag :type="getTagType(scope.row.实体分类)">
                  {{ scope.row.实体分类 }} - {{ getClassificationDesc(scope.row.实体分类) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="识别实体识别分数" label="识别分数">
              <template #default="scope">
                <el-progress 
                  :percentage="Math.round(scope.row.识别实体识别分数 * 100)" 
                  :color="getConfidenceColor(scope.row.识别实体识别分数)" 
                  :format="percent => percent + '%'"
                  :stroke-width="10"
                />
              </template>
            </el-table-column>
            <el-table-column prop="标准化术语" label="标准化术语" />
            <el-table-column prop="标准化术语中文" label="标准化术语中文" />
            <el-table-column prop="匹配的标准化术语准确度" label="匹配准确度">
              <template #default="scope">
                <el-progress 
                  :percentage="Math.round(scope.row.匹配的标准化术语准确度 * 100)" 
                  :color="getConfidenceColor(scope.row.匹配的标准化术语准确度)" 
                  :format="percent => percent + '%'"
                  :stroke-width="10"
                />
              </template>
            </el-table-column>
            <el-table-column label="位置">
              <template #default="scope">
                {{ scope.row.开始字符位置 }} - {{ scope.row.结束字符位置 }}
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <!-- 原始文本和标准化文本展示 -->
        <div class="result-cards">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-card shadow="hover" class="result-card">
                <template #header>
                  <div class="card-header">
                    <span>原文本</span>
                  </div>
                </template>
                <div class="text-content original">
                  {{ normalizationResults.用户输入内容 }}
                </div>
              </el-card>
            </el-col>
            
            <el-col :span="12">
              <el-card shadow="hover" class="result-card">
                <template #header>
                  <div class="card-header">
                    <span>文本及实体标记</span>
                    <el-button type="primary" size="small" plain @click="copyToClipboard(normalizationResults.用户输入内容 || '')">
                      复制
                    </el-button>
                  </div>
                </template>
                <div class="text-content normalized">
                  <span v-for="(char, index) in inputText" :key="index" 
                        :class="getHighlightClass(index)">{{ char }}</span>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'

// 术语分类数据
const classifications = [
  { code: 'E', name: 'Equities', description: '股权类（股票）' },
  { code: 'D', name: 'Debt Instruments', description: '债务工具' },
  { code: 'R', name: 'Entitlements (Rights)', description: '权利（如认购权）' },
  { code: 'T', name: 'Warrants', description: '权证' },
  { code: 'O', name: 'Options', description: '期权' },
  { code: 'F', name: 'Futures', description: '期货' },
  { code: 'H', name: 'Forward Contracts', description: '远期合约' },
  { code: 'S', name: 'Swaps', description: '互换' },
  { code: 'M', name: 'Miscellaneous', description: '其他（结构化产品等）' },
  { code: 'C', name: 'Collective Investments', description: '集合投资工具' },
  { code: 'L', name: 'Financing', description: '融资工具' },
  { code: 'Y', name: 'Non-listed & Other', description: '非上市及其他' },
  { code: 'N/A', name: 'N/A', description: '其他分类' }
]

// 状态变量
const inputText = ref('')
const loading = ref(false)
const normalizationResults = ref({})
const showResults = ref(false)  // 新增一个显式的状态标志

// 新增状态变量
const modelProvider = ref('siliconflow')
const modelName = ref('BAAI/bge-m3')  // 默认使用BAAI/bge-m3
const dbType = ref('chromadb')
const indexType = ref('hnsw')
const collectionName = ref('my_finterm_collection')
const selectedClassifications = ref(['E', 'D', 'F']) // 默认选择一些常用分类
const selectAllClasses = ref(false)
const isClassIndeterminate = ref(true)

// 数据库类型变更处理
const handleDbTypeChange = (val) => {
  if (val === 'chromadb') {
    indexType.value = 'hnsw'
  } else {
    indexType.value = ''
  }
}

// 计算属性
const hasResults = computed(() => {
  // 检查是否有处理结果 - 只要有用户输入内容或状态字段，就认为有结果
  return !!normalizationResults.status || !!normalizationResults.用户输入内容;
})

// 获取标签类型
const getTagType = (code) => {
  const tagTypes = {
    'E': 'danger',
    'D': 'primary',
    'F': 'warning',
    'O': 'success',
    'T': 'info'
  }
  return tagTypes[code] || ''
}

// 获取分类描述
const getClassificationDesc = (code) => {
  const classification = classifications.find(c => c.code === code)
  return classification ? classification.description : code
}

// 获取准确率颜色
const getConfidenceColor = (score) => {
  if (score >= 0.9) return '#67c23a'  // 高准确率 - 绿色
  if (score >= 0.7) return '#e6a23c'  // 中等准确率 - 黄色
  return '#f56c6c'  // 低准确率 - 红色
}

// 获取高亮类
const getHighlightClass = (index) => {
  // 查找此索引是否属于某个实体
  for (const entity of normalizationResults.实体详情 || []) {
    if (index >= entity.开始字符位置 && index < entity.结束字符位置) {
      return {
        'entity-highlight': true,
        [entity.实体分类]: true
      }
    }
  }
  return {}
}

// 全选处理函数 - 术语分类
const handleSelectAllClassesChange = (val) => {
  selectedClassifications.value = val ? classifications.map(item => item.code) : []
  isClassIndeterminate.value = false
}

// 术语分类选择处理函数
const handleClassificationsChange = (value) => {
  const checkedCount = value.length
  selectAllClasses.value = checkedCount === classifications.length
  isClassIndeterminate.value = checkedCount > 0 && checkedCount < classifications.length
}

// 复制到剪贴板
const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('复制成功')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

// 添加高亮JSON的函数
function highlightJson(json) {
  if (!json) return '';
  
  try {
    // 确保JSON是字符串，并格式化
    let formatted = typeof json === 'string' ? JSON.stringify(JSON.parse(json), null, 2) : JSON.stringify(json, null, 2);
    
    // 转义HTML字符
    formatted = formatted
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    
    // 添加语法高亮
    return formatted
      .replace(/"(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?/g, match => {
        const isKey = /:$/.test(match);
        return `<span class="${isKey ? 'json-key' : 'json-string'}">${match}</span>`;
      })
      .replace(/\b(true|false|null)\b/g, '<span class="json-boolean">$1</span>')
      .replace(/\b(\d+)([,\s]|$)/g, '<span class="json-number">$1</span>$2');
  } catch (e) {
    console.error('JSON高亮错误:', e);
    return typeof json === 'string' ? json : JSON.stringify(json, null, 2);
  }
}

// 执行术语标准化
const performNormalization = async () => {
  if (!inputText.value.trim()) {
    ElMessage.warning('请输入需要标准化的文本')
    return
  }

  if (selectedClassifications.value.length === 0) {
    ElMessage.warning('请至少选择一个术语分类')
    return
  }

  try {
    loading.value = true
    showResults.value = false  // 重置结果显示状态
    
    // 调用后端API
    const response = await fetch('/api/finterm/normalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: inputText.value,
        classifications: selectedClassifications.value,
        model_provider: modelProvider.value,
        model_name: modelName.value,
        db_type: dbType.value,
        index_type: indexType.value,
        collection_name: collectionName.value
      })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '处理请求时发生错误')
    }
    
    const data = await response.json()
    
    console.log('后端返回数据:', data)  // 调试输出
    
    // 显式设置结果数据，无论结果如何都显示
    normalizationResults.value = data
    showResults.value = true
    
    if (data.status === 'success') {
      ElMessage.success(`金融术语标准化完成，识别出 ${data.识别实体数 || 0} 个实体`)
    } else {
      ElMessage.warning('处理成功但可能存在问题，请查看返回结果')
    }
  } catch (error) {
    console.error('标准化处理错误:', error)
    ElMessage.error(`金融术语标准化失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.fin-term-normalization {
  padding: 20px;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
}

.input-section,
.model-section,
.db-section,
.classification-section,
.action-buttons,
.results-section,
.entity-details,
.json-result {
  margin-bottom: 30px;
}

.classification-options {
  margin-top: 15px;
}

.select-all-option {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
}

.selection-info {
  margin-left: 15px;
  color: #909399;
  font-size: 14px;
}

.classification-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.classification-item .code {
  font-weight: bold;
  min-width: 25px;
}

.action-buttons {
  margin-top: 30px;
  margin-bottom: 20px;
  text-align: center;
}

.result-cards {
  margin-bottom: 20px;
}

.result-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-content {
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 100px;
  max-height: 300px;
  overflow-y: auto;
  padding: 10px;
  border-radius: 4px;
  line-height: 1.5;
}

.text-content.original {
  background-color: #f9f9f9;
}

.text-content.normalized {
  background-color: #f0f9ff;
}

/* 实体高亮样式 */
.entity-highlight {
  padding: 2px 0;
  border-radius: 3px;
}

.E {
  background-color: rgba(255, 99, 132, 0.2);
  border-bottom: 2px solid rgba(255, 99, 132, 0.8);
}

.D {
  background-color: rgba(54, 162, 235, 0.2);
  border-bottom: 2px solid rgba(54, 162, 235, 0.8);
}

.R {
  background-color: rgba(255, 206, 86, 0.2);
  border-bottom: 2px solid rgba(255, 206, 86, 0.8);
}

.T {
  background-color: rgba(75, 192, 192, 0.2);
  border-bottom: 2px solid rgba(75, 192, 192, 0.8);
}

.O {
  background-color: rgba(153, 102, 255, 0.2);
  border-bottom: 2px solid rgba(153, 102, 255, 0.8);
}

.F {
  background-color: rgba(255, 159, 64, 0.2);
  border-bottom: 2px solid rgba(255, 159, 64, 0.8);
}

.H {
  background-color: rgba(199, 199, 199, 0.2);
  border-bottom: 2px solid rgba(199, 199, 199, 0.8);
}

.S {
  background-color: rgba(83, 225, 158, 0.2);
  border-bottom: 2px solid rgba(83, 225, 158, 0.8);
}

.M {
  background-color: rgba(223, 114, 255, 0.2);
  border-bottom: 2px solid rgba(223, 114, 255, 0.8);
}

.C {
  background-color: rgba(99, 255, 242, 0.2);
  border-bottom: 2px solid rgba(99, 255, 242, 0.8);
}

.L {
  background-color: rgba(255, 177, 99, 0.2);
  border-bottom: 2px solid rgba(255, 177, 99, 0.8);
}

.Y {
  background-color: rgba(176, 255, 99, 0.2);
  border-bottom: 2px solid rgba(176, 255, 99, 0.8);
}

.N\/A {
  background-color: rgba(200, 200, 200, 0.2);
  border-bottom: 2px solid rgba(200, 200, 200, 0.8);
}

.json-result {
  margin-top: 20px;
  margin-bottom: 30px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.json-card {
  margin-bottom: 0;
  border: none;
}

.json-content {
  white-space: pre-wrap;
  word-break: break-word;
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 14px;
  max-height: 400px;
  overflow-y: auto;
  color: #333;
  border: 1px solid #ebeef5;
  line-height: 1.5;
  counter-reset: line;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.loading-text {
  margin-top: 10px;
  color: #909399;
  font-size: 14px;
}

.result-info {
  margin-top: 20px;
  margin-bottom: 20px;
}

/* JSON语法高亮 */
:deep(.json-string) {
  color: #008000;
}

:deep(.json-key) {
  color: #0451a5;
  font-weight: bold;
}

:deep(.json-boolean) {
  color: #0000ff;
}

:deep(.json-number) {
  color: #098658;
}
</style> 