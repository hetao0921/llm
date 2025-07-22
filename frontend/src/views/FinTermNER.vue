<template>
  <div class="fin-term-ner">
    <h1>金融术语NER</h1>
    <p>在此页面进行金融术语的命名实体识别（NER）。</p>

    <div class="content">
      <!-- 输入框 -->
      <div class="input-section">
        <h2>输入文本</h2>
        <el-input 
          type="textarea" 
          v-model="inputText" 
          :rows="6" 
          placeholder="请输入需要进行命名实体识别的文本" 
        />
      </div>

      <!-- 术语分类 -->
      <div class="classification-section">
        <h2>术语分类</h2>
        <p>请选择需要识别的术语类型（可单选或多选）</p>
        
        <div class="classification-options">
          <!-- 全选选项 - 修改绑定方式 -->
          <div class="select-all-option">
            <el-checkbox 
              v-model="selectAll" 
              @change="handleSelectAllChange"
              :indeterminate="isIndeterminate"
              label="全选"
            >
              全选
            </el-checkbox>
            <span v-if="selectedClassifications.length > 0" class="selection-info">
              已选 {{ selectedClassifications.length }}/{{ classifications.length }} 项
            </span>
          </div>
          
          <el-divider />
          
          <!-- 分类选择组 -->
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
        <el-button type="primary" :loading="loading" @click="performNER">命名实体识别</el-button>
      </div>

      <!-- 结果展示 -->
      <div class="results-section" v-if="hasResults">
        <h2>识别结果</h2>
        
        <!-- 识别统计 -->
        <el-alert
          v-if="nerResults.summary"
          type="success"
          :title="`共识别出 ${nerResults.summary.totalEntities} 个实体`"
          :closable="false"
          show-icon
        />
        
        <!-- 实体详情表格 -->
        <div class="entity-details" v-if="nerResults.summary?.entityDetails?.length > 0">
          <h3>实体详情</h3>
          <el-table :data="nerResults.summary.entityDetails" style="width: 100%" border>
            <el-table-column prop="原始单词" label="原始单词" />
            <el-table-column prop="识别实体" label="识别实体" />
            <el-table-column prop="实体分类" label="实体分类">
              <template #default="scope">
                <el-tag :type="getTagType(scope.row.实体分类)">
                  {{ scope.row.实体分类 }} - {{ getClassificationDesc(scope.row.实体分类) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="识别分数" label="识别分数">
              <template #default="scope">
                <el-progress 
                  :percentage="Math.round(scope.row.识别分数 * 100)" 
                  :color="getConfidenceColor(scope.row.识别分数)" 
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
        
        <!-- 原文本高亮显示 -->
        <div class="text-highlight-section">
          <h3>文本高亮显示</h3>
          <div class="results-text-container">
            <div class="results-text">
              <template v-for="(char, index) in nerResults.text" :key="index">
                <span
                  :class="{
                    'entity': nerResults.entities[index]?.entity,
                    [nerResults.entities[index]?.entityType]: nerResults.entities[index]?.entity
                  }"
                  :title="nerResults.entities[index]?.entity ? 
                    `类型: ${getClassificationName(nerResults.entities[index]?.entityType)}\n准确率: ${(nerResults.entities[index]?.confidence * 100).toFixed(2)}%` : ''"
                >{{ char }}</span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
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
const selectedClassifications = ref([])  // 初始化为空数组
const loading = ref(false)
const nerResults = ref({
  text: '',
  entities: []
})
const selectAll = ref(true)  // 默认为全选
const isIndeterminate = ref(false)  // 默认不是中间状态

// 初始化检查选中状态
onMounted(() => {
  // 如果默认全选，则选中所有分类
  if (selectAll.value) {
    selectedClassifications.value = classifications.map(item => item.code)
  }
  
  // 检查初始状态
  const checkedCount = selectedClassifications.value.length
  selectAll.value = checkedCount === classifications.length
  isIndeterminate.value = checkedCount > 0 && checkedCount < classifications.length
  console.log('组件加载完成，初始选中状态:', {
    selectedItems: selectedClassifications.value,
    totalItems: classifications.length,
    selectAll: selectAll.value,
    isIndeterminate: isIndeterminate.value
  })
})

// 计算属性
const hasResults = computed(() => nerResults.value.text.length > 0)

// 获取分类名称
const getClassificationName = (code) => {
  const classification = classifications.find(c => c.code === code)
  return classification ? `${classification.description} (${classification.code})` : code
}

// 获取分类描述
const getClassificationDesc = (code) => {
  const classification = classifications.find(c => c.code === code)
  return classification ? classification.description : code
}

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

// 获取准确率颜色
const getConfidenceColor = (score) => {
  if (score >= 0.9) return '#67c23a'  // 高准确率 - 绿色
  if (score >= 0.7) return '#e6a23c'  // 中等准确率 - 黄色
  return '#f56c6c'  // 低准确率 - 红色
}

// 全选处理函数 - 修改实现方式
const handleSelectAllChange = (val) => {
  console.log('全选状态变更:', val)
  // 直接设置选中状态，避免使用三元运算符
  selectedClassifications.value = val ? 
    classifications.map(item => item.code) : 
    []
  
  // 确保状态一致
  nextTick(() => {
    console.log('全选处理完成，当前状态:', {
      selectAll: val,
      selectedItems: selectedClassifications.value.length,
      totalItems: classifications.length,
      isIndeterminate: selectedClassifications.value.length > 0 && 
                      selectedClassifications.value.length < classifications.length
    })
  })
}

// 单选处理函数
const handleClassificationsChange = (value) => {
  console.log('选中分类变更:', value)
  const checkedCount = value.length
  selectAll.value = checkedCount === classifications.length
  isIndeterminate.value = checkedCount > 0 && checkedCount < classifications.length
  
  // 手动触发一次检查，确保界面更新
  nextTick(() => {
    console.log('分类选择处理完成，当前状态:', {
      selectAll: selectAll.value,
      selectedClassifications: selectedClassifications.value,
      isIndeterminate: isIndeterminate.value
    })
  })
}

// 执行命名实体识别
const performNER = async () => {
  if (!inputText.value.trim()) {
    ElMessage.warning('请输入需要识别的文本')
    return
  }

  if (selectedClassifications.value.length === 0) {
    ElMessage.warning('请至少选择一个术语分类')
    return
  }

  try {
    loading.value = true
    
    // 调用后端API
    const response = await fetch('/api/finterm/ner', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: inputText.value,
        classifications: selectedClassifications.value
      })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '处理请求时发生错误')
    }
    
    const data = await response.json()
    
    if (data.status === 'success') {
      // 转换为所需格式
      const text = data.用户输入内容
      const entities = new Array(text.length).fill().map(() => ({
        entity: false,
        entityType: null,
        confidence: 0
      }))
      
      // 填充实体信息
      for (const entityDetail of data.实体详情) {
        const startPos = entityDetail.开始字符位置
        const endPos = entityDetail.结束字符位置
        const entityType = entityDetail.实体分类
        const confidence = entityDetail.识别分数
        
        for (let i = startPos; i < endPos; i++) {
          if (i >= 0 && i < text.length) {
            entities[i] = {
              entity: true,
              entityType: entityType,
              confidence: confidence
            }
          }
        }
      }
      
      nerResults.value = {
        text: text,
        entities: entities,
        summary: {
          totalEntities: data.识别实体数,
          selectedClassifications: data.选择分类,
          entityDetails: data.实体详情
        }
      }
      
      ElMessage.success(`命名实体识别完成，共识别出 ${data.识别实体数} 个实体`)
    } else {
      throw new Error('处理失败')
    }
  } catch (error) {
    console.error('NER处理错误:', error)
    ElMessage.error(`命名实体识别失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// 不再需要生成模拟数据的函数
</script>

<style scoped>
.fin-term-ner {
  padding: 20px;
}

.content {
  max-width: 1200px;
  margin: 0 auto;
}

.input-section,
.classification-section,
.action-buttons,
.results-section {
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
  text-align: center;
}

.entity-details {
  margin: 20px 0;
}

.text-highlight-section {
  margin-top: 30px;
}

.results-text-container {
  background-color: #f9f9f9;
  border-radius: 4px;
  padding: 15px;
  border: 1px solid #e0e0e0;
  max-height: 400px;
  overflow-y: auto;
}

.results-text {
  font-size: 16px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* 实体类型样式 */
.entity {
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
</style> 