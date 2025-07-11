<template>
  <div class="settings">
    <h1>设置</h1>
    <p>配置系统参数和选项。</p>
    
    <el-card class="main-content">
      <template #header>
        <div class="card-header">
          <span>系统设置</span>
        </div>
      </template>
      
      <div class="content">
        <p>此功能正在开发中...</p>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'Settings'
}
</script>

<style scoped>
.settings {
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

.content {
  padding: 20px;
  text-align: center;
  color: #909399;
}
</style> 