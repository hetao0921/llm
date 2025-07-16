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
          :action="uploadUrl"
          :headers="uploadHeaders"
        >
          <el-button type="primary">选择文件</el-button>
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
      </el-form-item>
    </el-form>

    <el-divider />
    <h2>已加载文件列表 <span v-if="loadedFiles.length">（共 {{ loadedFiles.length }} 条）</span></h2>
    <el-table :data="loadedFiles" style="width: 100%" v-loading="loadingList">
      <el-table-column prop="name" label="文件名" />
      <el-table-column prop="insert_time" label="加载时间" />
      <el-table-column prop="update_time" label="更新时间" />
      <el-table-column prop="status" label="文件状态">
        <template #default="scope">
          <el-tag :type="scope.row.status === '有效' ? 'success' : 'danger'">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
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

const uploadUrl = '/api/loading/files/upload'
const uploadHeaders = { Accept: 'application/json' }

const canLoad = computed(() => {
  return fileId.value && dbType.value && (dbType.value !== 'chromadb' || indexType.value) && provider.value && modelName.value && collectionName.value
})

function handleUploadSuccess(response, file, fileList) {
  // 兼容 el-upload 可能的 response 包裹
  const res = response && response.file_id ? response : (response && response.response ? response.response : null)
  console.log('upload response:', res)
  if (res && res.file_id) {
    fileId.value = res.file_id
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
    // fileId.value = '' // 不清空，便于多次加载
    // dbType.value = 'chromadb' // 保持默认
    // indexType.value = 'hnsw' // 保持默认
    // collectionName.value = 'my_finterm_collection' // 保持默认
    provider.value = 'siliconflow'
    modelName.value = 'BAAI/bge-m3'
  }
}

watch([fileId, dbType, indexType, provider, modelName], (vals) => {
  console.log('canLoad deps:', vals, 'canLoad:', canLoad.value)
})
</script>

<style scoped>
.fin-term-loading {
  padding: 20px;
}
.fin-term-form {
  max-width: 500px;
}
</style> 