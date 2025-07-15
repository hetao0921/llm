import { createRouter, createWebHistory } from 'vue-router'

// Import views
const Layout = () => import('../components/Layout.vue')
const FileLoading = () => import('../views/FileLoading.vue')
const DocumentChunking = () => import('../views/DocumentChunking.vue')
const DocumentParsing = () => import('../views/DocumentParsing.vue')
const VectorEmbedding = () => import('../views/VectorEmbedding.vue')
const VectorIndexing = () => import('../views/VectorIndexing.vue')
const TextGeneration = () => import('../views/TextGeneration.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: Layout,
      redirect: '/file-loading',
      children: [
        {
          path: 'file-loading',
          name: 'FileLoading',
          component: FileLoading,
          meta: { title: '文件加载' }
        },
        {
          path: 'document-chunking',
          name: 'DocumentChunking',
          component: DocumentChunking,
          meta: { title: '文档分块' }
        },
        {
          path: 'document-parsing',
          name: 'DocumentParsing',
          component: DocumentParsing,
          meta: { title: '文档解析' }
        },
        {
          path: 'vector-embedding',
          name: 'VectorEmbedding',
          component: VectorEmbedding,
          meta: { title: '向量嵌入' }
        },
        {
          path: 'vector-indexing',
          name: 'VectorIndexing',
          component: VectorIndexing,
          meta: { title: '向量索引' }
        },
        {
          path: 'text-generation',
          name: 'TextGeneration',
          component: TextGeneration,
          meta: { title: '文本生成' }
        },
        // 新增金融术语标准化工具箱相关路由
        {
          path: 'fin-term-loading',
          name: 'FinTermLoading',
          component: () => import('../views/FinTermLoading.vue'),
          meta: { title: '金融标准术语加载' }
        },
        {
          path: 'fin-term-ner',
          name: 'FinTermNER',
          component: () => import('../views/FinTermNER.vue'),
          meta: { title: '金融术语NER' }
        },
        {
          path: 'fin-term-normalization',
          name: 'FinTermNormalization',
          component: () => import('../views/FinTermNormalization.vue'),
          meta: { title: '金融术语标准化' }
        }
      ]
    }
  ]
})

// Update page title based on route meta
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - RAG Framework` : 'RAG Framework'
  next()
})

export default router 