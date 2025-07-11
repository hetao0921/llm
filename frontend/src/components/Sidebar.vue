<div class="sidebar-menu">
  <h2 class="sidebar-title">RAG 框架</h2>
  <el-menu
    router
    :default-active="activeIndex"
    class="sidebar-menu-items"
  >
    <el-menu-item index="/dashboard">
      <el-icon><DataBoard /></el-icon>
      <span>仪表盘</span>
    </el-menu-item>
    <el-menu-item index="/file-loading">
      <el-icon><Upload /></el-icon>
      <span>文件加载</span>
    </el-menu-item>
    <el-menu-item index="/document-chunking">
      <el-icon><Files /></el-icon>
      <span>文档分块</span>
    </el-menu-item>
    <el-menu-item index="/document-parsing">
      <el-icon><Reading /></el-icon>
      <span>文档解析</span>
    </el-menu-item>
  </el-menu>
</div>

<script>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataBoard, Upload, Files, Reading } from '@element-plus/icons-vue'

export default {
  name: 'Sidebar',
  components: {
    DataBoard,
    Upload,
    Files,
    Reading
  },
  setup() {
    const route = useRoute()
    const activeIndex = computed(() => route.path)
    
    return {
      activeIndex
    }
  }
}
</script>

<style scoped>
.sidebar-menu {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-title {
  padding: 16px;
  margin: 0;
  font-size: 18px;
  color: #409EFF;
  border-bottom: 1px solid #e6e6e6;
}

.sidebar-menu-items {
  flex: 1;
  border-right: none;
}
</style> 