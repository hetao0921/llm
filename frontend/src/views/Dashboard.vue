<template>
  <div class="dashboard">
    <h1>仪表盘</h1>
    <p>欢迎使用 RAG Framework</p>
    
    <div class="card-container">
      <div class="card" @click="navigateTo('/file-loading')">
        <h2>File Loading</h2>
        <p>Upload and process documents</p>
      </div>
      
      <div class="card" @click="navigateTo('/document-chunking')">
        <h2>Document Chunking</h2>
        <p>Split documents into chunks for processing</p>
      </div>
      
      <div class="card">
        <h2>Coming Soon</h2>
        <p>More features are under development</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const navigateTo = (path) => {
  router.push(path)
}
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

h1 {
  margin-bottom: 20px;
}

.card-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 30px;
}

.card {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

.card h2 {
  margin-top: 0;
  margin-bottom: 10px;
}

.card p {
  color: #666;
}
</style> 