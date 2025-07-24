<template>
  <div class="fin-term-loading">
    <h1>金融标准术语加载</h1>
    <el-form label-position="top" class="fin-term-form">
      <el-form-item label="选择文件">
        <el-upload
          class="upload-demo"
          :auto-upload="true"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :file-list="fileList"
          :limit="1"
          :on-exceed="handleExceed"
          :before-remove="handleBeforeRemove"
          :action="uploadUrl"
          :headers="uploadHeaders"
        >
          <el-button type="primary">选择文件</el-button>
          <template #tip>
            <div class="el-upload__tip">
              <p v-if="fileId">当前已上传文件ID: {{ fileId }}</p>
            </div>
          </template>
        </el-upload>
      </el-form-item>
      <el-form-item label="选择向量数据库类型">
        <el-select v-model="dbType" placeholder="请选择数据库类型" style="width: 200px" @change="onDbTypeChange">
          <el-option label="ChromaDB" value="chromadb" />
          <el-option label="Milvus" value="milvus" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="dbType === 'chromadb'" label="索引类型">
        <el-select v-model="indexType" placeholder="请选择索引类型" style="width: 200px">
          <el-option label="HNSW（分层可导航小世界图）" value="hnsw" />
          <el-option label="ANNOY（基于树的分区结构）" value="annoy" />
          <el-option label="FLAT（无索引）" value="flat" />
        </el-select>
      </el-form-item>
      <el-form-item label="集合名称">
        <el-input v-model="collectionName" placeholder="请输入集合名称" style="width: 300px" />
      </el-form-item>
      <el-form-item label="模型供应商">
        <el-select v-model="provider" placeholder="请选择模型供应商" style="width: 200px">
          <el-option label="siliconflow" value="siliconflow" />
        </el-select>
      </el-form-item>
      <el-form-item label="模型名称">
        <el-select v-model="modelName" placeholder="请选择模型名称" style="width: 300px">
          <el-option label="BAAI/bge-m3" value="BAAI/bge-m3" />
          <el-option label="netease-youdao/bce-embedding-base_v1" value="netease-youdao/bce-embedding-base_v1" />
          <el-option label="BAAI/bge-large-zh-v1.5" value="BAAI/bge-large-zh-v1.5" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="success" :disabled="!canLoad || loading" @click="handleLoad">加载</el-button>
        <span v-if="!canLoad" class="help-text">
          （请确保已上传文件并填写所有必填项）
        </span>
      </el-form-item>
    </el-form>

    <el-divider />
    <h2>已加载文件列表 <span v-if="loadedFiles.length">（共 {{ loadedFiles.length }} 条）</span></h2>
    <el-table :data="loadedFiles.slice(0, 10)" style="width: 100%" v-loading="loadingList">
      <el-table-column prop="name" label="文件名" />
      <el-table-column prop="insert_time" label="加载时间" />
      <el-table-column prop="update_time" label="更新时间" />
      <el-table-column prop="status" label="文件状态">
        <template #default="scope">
          <el-tag :type="scope.row.status === '有效' ? 'success' : 'danger'">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- 测试数据栏 -->
    <el-divider />
    <div class="test-section">
      <h2>测试数据</h2>
      <div class="test-form">
        <el-form label-position="top">
          <el-form-item label="测试数据">
            <el-input
              v-model="testInput"
              type="textarea"
              :rows="3"
              placeholder="请输入需要测试的金融术语，如：A股"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="testLoading" @click="handleTest">开始测试</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 测试结果展示 -->
      <div class="test-results" v-if="showTestResults">
        <h3>测试结果</h3>
        
        <!-- 查询信息 -->
        <el-alert
          v-if="testResult && testResult.查询信息"
          type="info"
          :closable="false"
          style="margin-bottom: 15px;"
        >
          <div class="query-info">
            <p><strong>查询文本:</strong> {{ testResult.查询信息.查询文本 }}</p>
            <p><strong>集合名称:</strong> {{ testResult.查询信息.集合名称 }}</p>
            <p><strong>集合大小:</strong> {{ testResult.查询信息.集合大小 }} 条数据</p>
            <p><strong>找到结果:</strong> {{ testResult.查询信息.结果数量 }} 条</p>
          </div>
        </el-alert>
        
        <!-- 匹配结果列表 -->
        <div v-if="testResult && testResult.匹配结果 && testResult.匹配结果.length > 0">
          <el-collapse accordion>
            <el-collapse-item 
              v-for="(match, index) in testResult.匹配结果" 
              :key="match.ID"
              :title="`结果 #${match.排名}: ${match.核心信息.原始术语} (${match.核心信息.中文标准化}) - 置信度: ${match.相似度.置信度}%`"
              :name="index"
            >
              <div class="match-details">
                <el-descriptions title="核心金融术语信息" :column="2" border>
                  <el-descriptions-item label="原始术语">{{ match.核心信息.原始术语 }}</el-descriptions-item>
                  <el-descriptions-item label="术语代码">{{ match.核心信息.术语代码 }}</el-descriptions-item>
                  <el-descriptions-item label="类别">{{ match.核心信息.类别 }}</el-descriptions-item>
                  <el-descriptions-item label="分类">{{ match.核心信息.分类 }}</el-descriptions-item>
                  <el-descriptions-item label="标准化形式">{{ match.核心信息.标准化形式 }}</el-descriptions-item>
                  <el-descriptions-item label="中文标准化">{{ match.核心信息.中文标准化 }}</el-descriptions-item>
                </el-descriptions>
                
                <el-descriptions title="相似度信息" :column="2" border>
                  <el-descriptions-item label="ID">{{ match.ID }}</el-descriptions-item>
                  <el-descriptions-item label="排名">第 {{ match.排名 }} 名</el-descriptions-item>
                  <el-descriptions-item label="距离">{{ match.相似度.距离 }}</el-descriptions-item>
                  <el-descriptions-item label="置信度">
                    <el-progress 
                      :percentage="match.相似度.置信度" 
                      :color="getConfidenceColor(match.相似度.置信度/100)"
                      :format="percent => percent + '%'"
                    />
                  </el-descriptions-item>
                </el-descriptions>
                
                <el-descriptions title="验证与时间信息" :column="3" border>
                  <el-descriptions-item label="状态">
                    <el-tag :type="match.验证信息.状态 === '有效' ? 'success' : 'danger'">
                      {{ match.验证信息.状态 }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="有效期开始">{{ match.验证信息.有效期开始 }}</el-descriptions-item>
                  <el-descriptions-item label="有效期结束">{{ match.验证信息.有效期结束 }}</el-descriptions-item>
                  <el-descriptions-item label="创建时间">{{ match.时间信息.创建时间 }}</el-descriptions-item>
                  <el-descriptions-item label="更新时间">{{ match.时间信息.更新时间 }}</el-descriptions-item>
                  <el-descriptions-item label="数据版本">{{ match.时间信息.数据版本 }}</el-descriptions-item>
                </el-descriptions>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
        
        <!-- 未找到结果时显示 -->
        <el-empty 
          v-else-if="testResult && testResult.status === 'success' && (!testResult.匹配结果 || testResult.匹配结果.length === 0)"
          description="未找到匹配结果"
        />
        
        <!-- 错误状态显示 -->
        <el-alert
          v-else-if="testResult && testResult.status === 'error'"
          type="error"
          :title="testResult.message || '查询出错'"
          :closable="false"
        />
        
        <!-- 完整JSON显示 -->
        <div class="full-json" v-if="testResult">
          <el-divider content-position="left">完整JSON数据</el-divider>
          <el-card shadow="hover" class="result-card">
            <div class="json-content" v-html="formatTestResult"></div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const fileList = ref([])
const fileId = ref('')
const dbType = ref('chromadb')
const indexType = ref('hnsw')
const provider = ref('siliconflow')
const modelName = ref('BAAI/bge-m3')
const collectionName = ref('my_finterm_collection')
const loadingList = ref(false)
const loading = ref(false)
const loadedFiles = ref([])

// 测试数据相关变量
const testInput = ref('')
const testLoading = ref(false)
const testResult = ref(null)
const showTestResults = ref(false)

const uploadUrl = '/api/loading/files/upload'
const uploadHeaders = { Accept: 'application/json' }

// 扩展 canLoad 计算属性，增加详细的日志
const canLoad = computed(() => {
  const result = fileId.value && dbType.value && 
    (dbType.value !== 'chromadb' || indexType.value) && 
    provider.value && modelName.value && collectionName.value
  
  console.log('canLoad check:', {
    fileId: Boolean(fileId.value),
    dbType: Boolean(dbType.value),
    indexTypeCheck: dbType.value !== 'chromadb' || Boolean(indexType.value),
    provider: Boolean(provider.value),
    modelName: Boolean(modelName.value),
    collectionName: Boolean(collectionName.value),
    result
  })
  
  return result
})

// 阻止文件被移除，因为这会导致fileId丢失
function handleBeforeRemove(file, fileList) {
  if (fileId.value) {
    ElMessage.warning('移除文件会导致当前选择的文件ID丢失，请谨慎操作')
    return false
  }
  return true
}

// 处理超出文件数量限制
function handleExceed() {
  ElMessage.warning('只能上传1个文件，请先移除当前文件再上传新文件')
}

function handleUploadSuccess(response, file, uploadFileList) {
  // 兼容 el-upload 可能的 response 包裹
  const res = response && response.file_id ? response : (response && response.response ? response.response : null)
  console.log('upload response:', res, 'file:', file, 'fileList:', uploadFileList)
  if (res && res.file_id) {
    fileId.value = res.file_id
    // 确保文件列表与上传的文件保持一致
    fileList.value = uploadFileList
    ElMessage.success('文件上传成功')
  } else {
    fileId.value = ''
    ElMessage.error('文件上传失败')
  }
}

function handleUploadError() {
  ElMessage.error('文件上传失败')
}

function onDbTypeChange() {
  if (dbType.value === 'chromadb') {
    indexType.value = 'hnsw'
  } else {
    indexType.value = ''
  }
}

async function handleLoad() {
  if (!fileId.value) {
    ElMessage.warning('请先上传文件')
    return
  }
  
  console.log('开始加载，当前状态:', {
    fileId: fileId.value,
    dbType: dbType.value,
    indexType: indexType.value,
    provider: provider.value,
    modelName: modelName.value,
    collectionName: collectionName.value
  })
  
  loading.value = true
  try {
    const body = {
      file_id: fileId.value,
      db_type: dbType.value,
      index_type: indexType.value,
      provider: provider.value,
      model_name: modelName.value,
      collection_name: collectionName.value
    }
    const resp = await fetch('/api/finterm/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await resp.json()
    if (resp.ok && data.status === 'success') {
      loadedFiles.value = data.files || []
      ElMessage.success('文件加载成功')
    } else {
      ElMessage.error(data.detail || '加载失败')
    }
  } catch (e) {
    ElMessage.error('请求失败: ' + (e.message || e))
  } finally {
    loading.value = false
    
    // 保留所有必要的值，使按钮保持可点击状态
    // 不重置 fileId，允许多次加载同一个文件
    // provider 和 modelName 也不应该重置为空值，而是保持现有值或恢复默认值
    if (!provider.value) provider.value = 'siliconflow'
    if (!modelName.value) modelName.value = 'BAAI/bge-m3'
    
    // 确保 dbType 和 collectionName 有值
    if (!dbType.value) dbType.value = 'chromadb'
    if (!collectionName.value) collectionName.value = 'my_finterm_collection'
    
    // 如果 dbType 是 chromadb，确保 indexType 有值
    if (dbType.value === 'chromadb' && !indexType.value) {
      indexType.value = 'hnsw'
    }
    
    console.log('加载完成后状态:', {
      fileId: fileId.value,
      dbType: dbType.value,
      indexType: indexType.value,
      provider: provider.value,
      modelName: modelName.value,
      collectionName: collectionName.value,
      canLoad: canLoad.value
    })
  }
}

// 加载已有的文件列表
async function fetchLoadedFiles() {
  try {
    loadingList.value = true
    const resp = await fetch('/api/loading/files')
    const data = await resp.json()
    if (resp.ok && Array.isArray(data)) {
      loadedFiles.value = data
    }
  } catch (e) {
    console.error('获取文件列表失败:', e)
  } finally {
    loadingList.value = false
  }
}

// 组件挂载时获取文件列表
onMounted(() => {
  fetchLoadedFiles()
})

watch([fileId, dbType, indexType, provider, modelName], (vals) => {
  console.log('canLoad deps changed:', vals, 'canLoad:', canLoad.value)
})

// 格式化测试结果
const formatTestResult = computed(() => {
  if (!testResult.value) return '';
  
  try {
    // 格式化JSON并添加高亮
    const formattedJson = JSON.stringify(testResult.value, null, 2);
    
    return highlightJson(formattedJson);
  } catch (e) {
    console.error('格式化测试结果失败:', e);
    return JSON.stringify(testResult.value, null, 2);
  }
});

// 高亮JSON
function highlightJson(json) {
  if (!json) return '';
  
  try {
    // 转义HTML字符
    const escaped = json
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    
    // 添加语法高亮
    return escaped
      .replace(/"(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?/g, match => {
        const isKey = /:$/.test(match);
        return `<span class="${isKey ? 'json-key' : 'json-string'}">${match}</span>`;
      })
      .replace(/\b(true|false|null)\b/g, '<span class="json-boolean">$1</span>')
      .replace(/\b(\d+)([,\s]|$)/g, '<span class="json-number">$1</span>$2');
  } catch (e) {
    console.error('JSON高亮处理失败:', e);
    return json;
  }
}

// 执行测试
async function handleTest() {
  if (!testInput.value.trim()) {
    ElMessage.warning('请输入测试数据');
    return;
  }
  
  if (!collectionName.value) {
    ElMessage.warning('请指定集合名称');
    return;
  }
  
  testLoading.value = true;
  showTestResults.value = false;
  
  try {
    // 调用测试API
    const resp = await fetch('/api/finterm/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: testInput.value,
        collection_name: collectionName.value,
        model_provider: provider.value,
        model_name: modelName.value,
        db_type: dbType.value,
        index_type: indexType.value
      })
    });
    
    const data = await resp.json();
    testResult.value = data;
    showTestResults.value = true;
    
    if (data.status === 'success') {
      if (data.匹配结果 && data.匹配结果.length > 0) {
        ElMessage.success(`测试成功，找到 ${data.匹配结果.length} 个匹配结果`);
      } else {
        ElMessage.info('测试成功，但未找到匹配的术语');
      }
    } else {
      ElMessage.warning(data.message || '测试返回了错误状态');
    }
  } catch (e) {
    console.error('测试请求失败:', e);
    ElMessage.error('测试请求失败: ' + (e.message || e));
  } finally {
    testLoading.value = false;
  }
}

// 获取准确率颜色
function getConfidenceColor(score) {
  if (score >= 0.9) return '#67c23a'  // 高准确率 - 绿色
  if (score >= 0.7) return '#e6a23c'  // 中等准确率 - 黄色
  return '#f56c6c'  // 低准确率 - 红色
}
</script>

<style scoped>
.fin-term-loading {
  padding: 20px;
}
.fin-term-form {
  max-width: 500px;
}
.help-text {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.test-section {
  margin-top: 20px;
}

.test-form {
  max-width: 800px;
}

.test-results {
  margin-top: 20px;
}

.query-info {
  margin: 0;
}

.query-info p {
  margin: 5px 0;
}

.match-details {
  margin-bottom: 15px;
}

.result-card {
  margin-bottom: 20px;
}

.full-json {
  margin-top: 30px;
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
}

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