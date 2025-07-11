import { createPinia } from 'pinia'
import { useLoadingStore } from './loading'
import { useChunkingStore } from './chunking'
import { useParsingStore } from './parsing'
import { useEmbeddingStore } from './embedding'
import { useIndexingStore } from './indexing'
import { useGenerationStore } from './generation'

export default createPinia() 