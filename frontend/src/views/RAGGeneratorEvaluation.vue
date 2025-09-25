<template>
  <div class="rag-generator-evaluation">
    <div class="page-header">
      <h1>RAG系统生成器评估</h1>
      <p>评估RAG生成器的性能指标</p>
    </div>

    <div class="evaluation-form">
      <el-card class="form-card">
        <template #header>
          <div class="card-header">
            <span>评估配置</span>
          </div>
        </template>

        <!-- 系统类型选择 -->
        <div class="form-item">
          <label class="form-label">系统类型</label>
          <el-select 
            v-model="systemType" 
            placeholder="请选择系统类型"
            class="full-width-select"
          >
            <el-option label="生成评估" value="generation" />
            <el-option label="检索评估" value="retrieval" />
          </el-select>
        </div>

        <!-- 生成子类型选择 -->
        <div class="form-item" v-if="systemType === 'generation'">
          <label class="form-label">生成子类型</label>
          <el-select 
            v-model="generationSubType" 
            placeholder="请选择生成子类型"
            class="full-width-select"
          >
            <el-option label="txt2SQL" value="txt2sql" />
          </el-select>
        </div>

        <!-- 问题输入框 -->
        <div class="form-item" v-if="generationSubType === 'txt2sql'">
          <label class="form-label">检索SQL问题</label>
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            placeholder="请输入要检索的SQL问题..."
            class="full-width-input"
          />
        </div>

        <!-- 标准化生成列表上传 -->
        <div class="form-item" v-if="generationSubType === 'txt2sql'">
          <label class="form-label">标准化生成列表</label>
          <el-upload
            ref="uploadRef"
            class="upload-demo"
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :before-upload="beforeUpload"
            accept=".txt,.csv,.json"
            :limit="1"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .txt, .csv, .json 格式文件
              </div>
            </template>
          </el-upload>
        </div>

        <!-- 提交按钮 -->
        <div class="form-item submit-item">
          <el-button 
            type="primary" 
            size="large"
            :loading="isSubmitting"
            @click="submitEvaluation"
            class="submit-button"
          >
            {{ isSubmitting ? '评估中...' : '提交评测' }}
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 生成结果展示 -->
    <div class="results-section" v-if="generationResults">
      <el-card class="results-card">
        <template #header>
          <div class="card-header">
            <span>生成器输出结果</span>
          </div>
        </template>
        <div class="generation-output">
          <pre class="output-content">{{ generationResults }}</pre>
        </div>
      </el-card>
    </div>

    <!-- 评估指标展示 -->
    <div class="metrics-section" v-if="evaluationMetrics">
      <el-card class="metrics-card">
        <template #header>
          <div class="card-header">
            <span>评估计算结果</span>
          </div>
        </template>
        <div class="metrics-grid">
          <div class="metric-item">
            <div class="metric-label">精确匹配率</div>
            <div class="metric-value">{{ evaluationMetrics.exact_match_rate?.toFixed(4) || 'N/A' }}</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">检索相关性</div>
            <div class="metric-value">{{ evaluationMetrics.retrieval_relevance?.toFixed(4) || 'N/A' }}</div>
          </div>
          <div class="metric-item">
            <div class="metric-label">生成器上下文利用度</div>
            <div class="metric-value">{{ evaluationMetrics.context_utilization?.toFixed(4) || 'N/A' }}</div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { ragGeneratorEvaluationApi } from '@/services/api'

// 响应式数据
const systemType = ref('generation') // 默认选择生成评估
const generationSubType = ref('txt2sql') // 默认选择txt2SQL
const question = ref('')
const uploadedFile = ref(null)
const isSubmitting = ref(false)
const generationResults = ref('')
const evaluationMetrics = ref(null)

// 文件上传处理
const handleFileChange = (file) => {
  uploadedFile.value = file.raw
  console.log('文件已选择:', file.name)
}

const beforeUpload = (file) => {
  const isValidType = ['text/plain', 'text/csv', 'application/json'].includes(file.type) ||
                     file.name.endsWith('.txt') || 
                     file.name.endsWith('.csv') || 
                     file.name.endsWith('.json')
  
  if (!isValidType) {
    ElMessage.error('只支持 .txt, .csv, .json 格式的文件!')
    return false
  }
  
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('文件大小不能超过 10MB!')
    return false
  }
  
  return false // 阻止自动上传
}

// 提交评估
const submitEvaluation = async () => {
  // 验证输入
  if (!question.value.trim()) {
    ElMessage.warning('请输入检索SQL问题')
    return
  }
  
  if (!uploadedFile.value) {
    ElMessage.warning('请上传标准化生成列表文件')
    return
  }

  isSubmitting.value = true
  
  try {
    // 创建FormData
    const formData = new FormData()
    formData.append('system_type', systemType.value)
    formData.append('generation_sub_type', generationSubType.value)
    formData.append('question', question.value)
    formData.append('standard_list', uploadedFile.value)
    
    console.log('提交评估数据:', {
      systemType: systemType.value,
      generationSubType: generationSubType.value,
      question: question.value,
      fileName: uploadedFile.value.name
    })
    
    // 调用后端API
    const response = await ragGeneratorEvaluationApi.submitGeneratorEvaluation(formData)
    
    if (response.data.success) {
      generationResults.value = response.data.generation_results
      evaluationMetrics.value = response.data.evaluation_metrics
      ElMessage.success('评估完成!')
    } else {
      ElMessage.error(response.data.message || '评估失败')
    }
    
  } catch (error) {
    console.error('评估失败:', error)
    ElMessage.error('评估失败，请重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.rag-generator-evaluation {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  color: #303133;
  margin-bottom: 10px;
  font-size: 28px;
  font-weight: 600;
}

.page-header p {
  color: #606266;
  font-size: 16px;
}

.evaluation-form {
  margin-bottom: 30px;
}

.form-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #606266;
  font-size: 14px;
}

.full-width-select,
.full-width-input {
  width: 100%;
}

.submit-item {
  text-align: center;
  margin-top: 30px;
}

.submit-button {
  width: 200px;
  height: 45px;
  font-size: 16px;
}

.results-section,
.metrics-section {
  margin-bottom: 30px;
}

.results-card,
.metrics-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.generation-output {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
}

.output-content {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #303133;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px;
  padding: 20px 0;
}

.metric-item {
  text-align: center;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.metric-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: #67c23a;
}

.upload-demo {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 120px;
}

:deep(.el-upload__tip) {
  color: #909399;
  font-size: 12px;
  margin-top: 7px;
}
</style>
