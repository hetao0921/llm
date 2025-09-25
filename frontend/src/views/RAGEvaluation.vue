<template>
  <div class="rag-evaluation">
    <h1>RAG系统评估</h1>
    <p>评估RAG系统的检索和生成性能。</p>
    
    <el-card class="evaluation-section">
      <template #header>
        <div class="card-header">
          <span>评估配置</span>
        </div>
      </template>
      
      <el-form :model="evaluationForm" label-position="top" class="evaluation-form">
        <el-form-item label="系统类型">
          <el-select 
            v-model="evaluationForm.systemType" 
            placeholder="选择系统类型"
            @change="handleSystemTypeChange"
            style="width: 100%"
          >
            <el-option label="生成评估" value="generation" />
            <el-option label="检索评估" value="retrieval" />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="evaluationForm.systemType === 'retrieval'" label="检索子类型">
          <el-select 
            v-model="evaluationForm.retrievalSubType" 
            placeholder="选择检索子类型"
            @change="handleRetrievalSubTypeChange"
            style="width: 100%"
          >
            <el-option label="txt2SQL" value="txt2sql" />
          </el-select>
        </el-form-item>

        <!-- txt2SQL 评估配置 -->
        <div v-if="evaluationForm.systemType === 'retrieval' && evaluationForm.retrievalSubType === 'txt2sql'" class="txt2sql-config">
          <el-divider content-position="left">txt2SQL 评估配置</el-divider>
          
          <el-form-item label="上传原始表结构">
            <el-upload
              class="upload-demo"
              :action="uploadUrl"
              :headers="uploadHeaders"
              :auto-upload="false"
              :on-change="handleSchemaFileChange"
              :on-remove="handleSchemaFileRemove"
              :before-upload="beforeUpload"
              :limit="10"
              multiple
              accept=".sql,.txt"
            >
              <template #trigger>
                <el-button type="primary">选择表结构文件</el-button>
              </template>
              <template #tip>
                <div class="el-upload__tip">
                  支持多个SQL文件，包括建表语句和初始化数据
                </div>
              </template>
            </el-upload>
          </el-form-item>
          
          <el-form-item label="上传问答对">
            <el-upload
              class="upload-demo"
              :action="uploadUrl"
              :headers="uploadHeaders"
              :auto-upload="false"
              :on-change="handleQAPairFileChange"
              :on-remove="handleQAPairFileRemove"
              :before-upload="beforeUpload"
              :limit="1"
              accept=".json,.txt"
            >
              <template #trigger>
                <el-button type="primary">选择问答对文件</el-button>
              </template>
              <template #tip>
                <div class="el-upload__tip">
                  支持JSON格式的问答对文件
                </div>
              </template>
            </el-upload>
          </el-form-item>
        </div>

        <!-- 提交按钮 -->
        <el-form-item>
          <el-button 
            type="primary" 
            size="large"
            :loading="evaluating"
            :disabled="!canSubmit"
            @click="submitEvaluation"
            class="submit-button"
          >
            {{ evaluating ? '评估中...' : '提交评测' }}
          </el-button>
          <el-button 
            type="success" 
            size="large"
            @click="showTestResults"
            class="test-button"
          >
            显示测试结果
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 评估结果 -->
    <el-card v-if="evaluationResult" class="result-section">
      <template #header>
        <div class="card-header">
          <span>评估结果</span>
          <el-button type="primary" @click="exportResults">导出结果</el-button>
        </div>
      </template>
      
      <div class="result-content">
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ evaluationResult.recall?.toFixed(4) || 'N/A' }}</div>
              <div class="metric-label">召回率 (Recall)</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ evaluationResult.precision?.toFixed(4) || 'N/A' }}</div>
              <div class="metric-label">精确率 (Precision)</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ evaluationResult.accuracy?.toFixed(4) || 'N/A' }}</div>
              <div class="metric-label">准确率 (Accuracy)</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ evaluationResult.f2_score?.toFixed(4) || 'N/A' }}</div>
              <div class="metric-label">F2值 (F2-Score)</div>
            </div>
          </el-col>
        </el-row>

        <!-- 详细结果 -->
        <el-divider content-position="left">详细结果</el-divider>
        <div class="detailed-results">
          <el-table :data="evaluationResult.details || []" style="width: 100%">
            <el-table-column prop="question" label="问题" width="300" />
            <el-table-column prop="expected_sql" label="期望SQL" width="300" />
            <el-table-column prop="generated_sql" label="生成SQL" width="300" />
            <el-table-column prop="is_correct" label="是否正确" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.is_correct ? 'success' : 'danger'">
                  {{ scope.row.is_correct ? '正确' : '错误' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="similarity" label="相似度" width="100">
              <template #default="scope">
                {{ scope.row.similarity?.toFixed(4) || 'N/A' }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { evaluationApi } from '../services/api'

// 响应式数据
const evaluationForm = ref({
  systemType: 'retrieval',  // 默认选择检索评估
  retrievalSubType: 'txt2sql'  // 默认选择txt2SQL
})

const schemaFiles = ref([])
const qaPairFiles = ref([])
const evaluating = ref(false)
const evaluationResult = ref(null)

// 计算属性
const canSubmit = computed(() => {
  if (!evaluationForm.value.systemType) return false
  
  if (evaluationForm.value.systemType === 'retrieval' && 
      evaluationForm.value.retrievalSubType === 'txt2sql') {
    return schemaFiles.value.length > 0 && qaPairFiles.value.length > 0
  }
  
  return true
})

const uploadUrl = computed(() => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl}/api/evaluation/upload`
})

const uploadHeaders = computed(() => ({
  'Accept': 'application/json'
}))

// 方法
const handleSystemTypeChange = (value) => {
  evaluationForm.value.retrievalSubType = ''
  schemaFiles.value = []
  qaPairFiles.value = []
  evaluationResult.value = null
}

const handleRetrievalSubTypeChange = (value) => {
  schemaFiles.value = []
  qaPairFiles.value = []
  evaluationResult.value = null
}

const handleSchemaFileChange = (file, fileList) => {
  schemaFiles.value = fileList
}

const handleSchemaFileRemove = (file, fileList) => {
  schemaFiles.value = fileList
}

const handleQAPairFileChange = (file, fileList) => {
  qaPairFiles.value = fileList
}

const handleQAPairFileRemove = (file, fileList) => {
  qaPairFiles.value = fileList
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
    'application/sql',
    'text/plain',
    'application/json',
    'text/sql'
  ]
  
  if (!allowedTypes.includes(file.type) && !file.name.endsWith('.sql') && !file.name.endsWith('.json') && !file.name.endsWith('.txt')) {
    ElMessage.error('不支持的文件类型，请上传 .sql, .json 或 .txt 文件')
    return false
  }
  
  return true
}

const submitEvaluation = async () => {
  if (!canSubmit.value) {
    ElMessage.warning('请完成所有必要的配置')
    return
  }

  evaluating.value = true
  
  try {
    const formData = new FormData()
    formData.append('system_type', evaluationForm.value.systemType)
    
    if (evaluationForm.value.retrievalSubType) {
      formData.append('retrieval_sub_type', evaluationForm.value.retrievalSubType)
    }
    
    // 添加表结构文件
    schemaFiles.value.forEach((file, index) => {
      formData.append(`schema_files`, file.raw)
    })
    
    // 添加问答对文件
    qaPairFiles.value.forEach((file, index) => {
      formData.append(`qa_pair_files`, file.raw)
    })

    const response = await evaluationApi.submitEvaluation(formData)
    
    if (response && response.data) {
      const evaluationId = response.data.evaluation_id
      ElMessage.success('评估任务已提交，正在处理中...')
      
      // 轮询获取评估结果
      await pollEvaluationResult(evaluationId)
    } else {
      ElMessage.error('评估失败，请重试')
    }
  } catch (error) {
    console.error('Evaluation error:', error)
    ElMessage.error('评估失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    evaluating.value = false
  }
}

const pollEvaluationResult = async (evaluationId) => {
  const maxAttempts = 60 // 最多轮询60次
  let attempts = 0
  
  const poll = async () => {
    try {
      const response = await evaluationApi.getEvaluationResult(evaluationId)
      
      if (response && response.data) {
        const result = response.data
        
        if (result.status === 'completed') {
          // 评估完成，显示结果
          evaluationResult.value = result
          ElMessage.success('评估完成！')
          return
        } else if (result.status === 'failed') {
          ElMessage.error('评估失败')
          return
        } else if (result.status === 'processing') {
          // 仍在处理中，继续轮询
          attempts++
          if (attempts < maxAttempts) {
            setTimeout(poll, 2000) // 2秒后再次轮询
          } else {
            ElMessage.error('评估超时，请重试')
          }
        }
      }
    } catch (error) {
      console.error('Polling error:', error)
      attempts++
      if (attempts < maxAttempts) {
        setTimeout(poll, 2000)
      } else {
        ElMessage.error('获取评估结果失败')
      }
    }
  }
  
  // 开始轮询
  poll()
}

const exportResults = () => {
  if (!evaluationResult.value) {
    ElMessage.warning('没有可导出的结果')
    return
  }
  
  const dataStr = JSON.stringify(evaluationResult.value, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `rag_evaluation_result_${new Date().getTime()}.json`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('结果已导出')
}
</script>

<style scoped>
.rag-evaluation {
  padding: 20px;
}

.evaluation-section,
.result-section {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.evaluation-form {
  padding: 20px;
}

.txt2sql-config {
  margin-top: 20px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.submit-button {
  width: 200px;
  height: 50px;
  font-size: 16px;
}

.result-content {
  padding: 20px;
}

.metric-card {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.metric-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.metric-label {
  font-size: 14px;
  opacity: 0.9;
}

.detailed-results {
  margin-top: 20px;
}

:deep(.el-upload__tip) {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

:deep(.el-upload-list) {
  margin-top: 10px;
}

:deep(.el-divider__text) {
  font-weight: 600;
  color: #409eff;
}
</style>
