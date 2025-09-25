<template>
  <div class="sidebar">
    <div class="logo-container">
      <h2 class="logo">RAG Framework</h2>
    </div>
    <el-menu
      router
      :default-active="activeRoute"
      class="sidebar-menu"
      background-color="#001529"
      text-color="#fff"
      active-text-color="#409eff"
    >
      <el-menu-item index="/file-loading">
        <el-icon><Upload /></el-icon>
        <span>文件加载</span>
      </el-menu-item>
      <el-menu-item index="/document-chunking" class="highlighted-menu-item">
        <el-icon><Document /></el-icon>
        <span>文档分块</span>
        <el-tag size="small" type="success" class="menu-tag">进行中</el-tag>
      </el-menu-item>
      <el-menu-item index="/document-parsing">
        <el-icon><Reading /></el-icon>
        <span>文档解析</span>
      </el-menu-item>
      <el-menu-item index="/vector-embedding">
        <el-icon><Connection /></el-icon>
        <span>向量嵌入</span>
      </el-menu-item>
      <el-menu-item index="/vector-indexing">
        <el-icon><Collection /></el-icon>
        <span>向量索引</span>
      </el-menu-item>
      <el-menu-item index="/text-generation">
        <el-icon><ChatDotRound /></el-icon>
        <span>文本生成</span>
      </el-menu-item>
      <!-- 新增金融术语标准化工具箱主菜单及其子菜单 -->
      <el-sub-menu index="fin-term-toolbox">
        <template #title>
          <el-icon><Collection /></el-icon>
          <span>金融术语标准化工具箱</span>
        </template>
        <el-menu-item index="/fin-term-loading">金融标准术语加载</el-menu-item>
        <el-menu-item index="/fin-term-ner">金融术语NER</el-menu-item>
        <el-menu-item index="/fin-term-normalization">金融术语标准化</el-menu-item>
      </el-sub-menu>
      <el-sub-menu index="rag-evaluation">
        <template #title>
          <el-icon><TrendCharts /></el-icon>
          <span>RAG系统评估</span>
        </template>
        <el-menu-item index="/rag-retriever-evaluation">RAG系统检索器评估</el-menu-item>
        <el-menu-item index="/rag-generator-evaluation">RAG系统生成器评估</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Upload, Document, Reading, Connection, Collection, ChatDotRound, TrendCharts } from '@element-plus/icons-vue'

const route = useRoute()
const activeRoute = computed(() => route.path)
</script>

<style scoped>
.sidebar {
  width: 210px;
  height: 100%;
  background-color: #001529;
  color: white;
  overflow-y: auto;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.35);
}

.logo-container {
  height: 60px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.logo {
  color: white;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  text-align: center;
}

.sidebar-menu {
  border-right: none;
}

.el-menu-item, .el-sub-menu {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.el-sub-menu :deep(.el-sub-menu__title) {
  border-bottom: none;
}

.highlighted-menu-item {
  background-color: rgba(64, 158, 255, 0.1) !important;
  position: relative;
}

.highlighted-menu-item:hover {
  background-color: rgba(64, 158, 255, 0.2) !important;
}

.menu-tag {
  position: absolute;
  right: 10px;
  font-size: 10px;
  padding: 0 5px;
  height: 20px;
  line-height: 20px;
  border-radius: 10px;
}
</style> 