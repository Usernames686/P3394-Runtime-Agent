<template>
  <div class="memory-page">
    <header class="memory-header">
      <div>
        <div class="eyebrow">P3394 Memory Atlas</div>
        <h1>记忆图谱</h1>
        <p>Sigma.js + Graphology WebGL 图谱，本地 SQLite 持久化知识、人物、项目、工具和长期关系。</p>
      </div>
      <div class="header-actions">
        <n-button secondary :loading="loading" @click="loadAll">刷新</n-button>
        <n-button type="primary" :loading="seeding" @click="seedDemo">生成大型示例图</n-button>
      </div>
    </header>

    <n-alert v-if="error" type="error" class="memory-alert">
      {{ error }}
    </n-alert>

    <section class="stats-row">
      <div class="stat">
        <span>节点</span>
        <strong>{{ graph.node_count || 0 }}</strong>
      </div>
      <div class="stat">
        <span>关系</span>
        <strong>{{ graph.edge_count || 0 }}</strong>
      </div>
      <div class="stat">
        <span>知识</span>
        <strong>{{ knowledge.length }}</strong>
      </div>
      <div class="stat">
        <span>引擎</span>
        <strong>Sigma WebGL</strong>
      </div>
    </section>

    <section class="memory-workbench">
      <main class="atlas-panel">
        <div class="atlas-toolbar">
          <n-input
            v-model:value="searchText"
            clearable
            size="small"
            placeholder="搜索节点、关系、证据"
            class="atlas-search"
            @keyup.enter="focusFirstMatch"
          />
          <div class="toolbar-actions">
            <n-button
              v-for="mode in viewModes"
              :key="mode.value"
              size="small"
              :type="viewMode === mode.value ? 'primary' : 'default'"
              :secondary="viewMode !== mode.value"
              @click="setViewMode(mode.value)"
            >
              {{ mode.label }}
            </n-button>
            <n-button size="small" secondary @click="resetCamera">重置视图</n-button>
            <n-button size="small" tertiary @click="focusFirstMatch">聚焦搜索</n-button>
          </div>
        </div>

        <div class="graph-shell">
          <div ref="graphEl" class="graph-canvas"></div>
          <div class="graph-overlay">
            <div v-for="item in legendItems" :key="item.kind" class="legend-item">
              <span class="legend-dot" :style="{ background: item.color }"></span>
              {{ item.label }}
            </div>
          </div>
          <div v-if="!hasGraph" class="empty-graph">
            <h2>还没有图谱节点</h2>
            <p>点击“生成大型示例图”，先看一张更接近真实记忆网络的图。</p>
          </div>
        </div>
      </main>

      <aside class="inspector-panel">
        <section class="inspector-section selected-node" v-if="selectedNode">
          <div class="section-title">当前节点</div>
          <h2>{{ selectedNode.label }}</h2>
          <p>{{ selectedNode.summary || '这个节点暂时没有摘要。' }}</p>
          <div class="node-meta">
            <span>{{ kindLabel(selectedNode.kind) }}</span>
            <span>{{ selectedNode.degree }} 条连接</span>
          </div>
          <div v-if="selectedRelations.length" class="relation-list">
            <article v-for="edge in selectedRelations" :key="edge.id" class="relation-item">
              <strong>{{ edge.source_label }} -- {{ edge.relation }} -- {{ edge.target_label }}</strong>
              <p>{{ edge.evidence || '暂无证据' }}</p>
            </article>
          </div>
        </section>

        <section class="inspector-section">
          <div class="section-header">
            <div class="section-title">每日记忆</div>
            <div class="daily-actions">
              <n-button
                size="tiny"
                :type="timelineDays === 7 ? 'primary' : 'default'"
                :secondary="timelineDays !== 7"
                @click="setTimelineDays(7)"
              >
                近 7 天
              </n-button>
              <n-button
                size="tiny"
                :type="timelineDays === 30 ? 'primary' : 'default'"
                :secondary="timelineDays !== 30"
                @click="setTimelineDays(30)"
              >
                近 30 天
              </n-button>
              <n-button size="tiny" secondary :loading="generatingDailyMemory" @click="generateTodayMemory">今日生成</n-button>
            </div>
          </div>
          <div v-if="dailyNotes.length" class="daily-note-list">
            <article
              v-for="note in dailyNotes.slice(0, timelineDays)"
              :key="note.id"
              class="daily-note-item"
              :class="{ active: selectedNode?.label === note.date_key }"
              @click="focusDailyNote(note)"
            >
              <div class="daily-note-head">
                <strong>{{ note.date_key }}</strong>
                <span>{{ note.entry_count || 0 }} 条</span>
              </div>
              <div class="daily-note-tags" v-if="(note.wikilinks || []).length || (note.markdown_tags || []).length">
                <span v-for="link in (note.wikilinks || []).slice(0, 4)" :key="`link-${note.id}-${link}`">[[{{ link }}]]</span>
                <span v-for="tag in (note.markdown_tags || []).slice(0, 4)" :key="`tag-${note.id}-${tag}`">#{{ tag }}</span>
              </div>
              <p class="daily-note-path">{{ note.path }}</p>
              <pre>{{ note.preview }}</pre>
            </article>
          </div>
          <n-empty v-else description="还没有每日记忆" />
        </section>

        <section class="inspector-section">
          <div class="section-title">图谱检索</div>
          <div v-if="filteredNodes.length" class="node-list">
            <button
              v-for="node in filteredNodes.slice(0, 12)"
              :key="node.id"
              class="node-row"
              :class="{ active: selectedNodeId === node.id }"
              @click="selectNode(node.id, true)"
            >
              <span class="node-dot" :style="{ background: kindColor(node.kind) }"></span>
              <span>{{ node.label }}</span>
              <small>{{ node.degree }}</small>
            </button>
          </div>
          <n-empty v-else description="没有匹配节点" />
        </section>

        <section class="inspector-section">
          <div class="section-title">新增关系</div>
          <n-form label-placement="top" size="small">
            <n-form-item label="源节点">
              <n-input v-model:value="relationForm.source_label" placeholder="例如：你" />
            </n-form-item>
            <n-form-item label="关系">
              <n-input v-model:value="relationForm.relation" placeholder="例如：owns / uses / works_on" />
            </n-form-item>
            <n-form-item label="目标节点">
              <n-input v-model:value="relationForm.target_label" placeholder="例如：P3394 Runtime Agent" />
            </n-form-item>
            <n-form-item label="证据">
              <n-input v-model:value="relationForm.evidence" type="textarea" :rows="3" placeholder="这条关系从哪里来" />
            </n-form-item>
            <n-button block type="primary" :loading="savingRelation" @click="saveRelation">保存关系</n-button>
          </n-form>
        </section>

        <section class="inspector-section">
          <div class="section-title">新增知识</div>
          <n-form label-placement="top" size="small">
            <n-form-item label="标题">
              <n-input v-model:value="knowledgeForm.title" placeholder="例如：项目偏好" />
            </n-form-item>
            <n-form-item label="内容">
              <n-input v-model:value="knowledgeForm.content" type="textarea" :rows="4" placeholder="要让 P3394 记住的内容" />
            </n-form-item>
            <n-button block secondary :loading="savingKnowledge" @click="saveKnowledge">保存知识</n-button>
          </n-form>
        </section>

        <section class="inspector-section">
          <div class="section-title">最近知识</div>
          <div v-if="knowledge.length" class="knowledge-list">
            <article v-for="item in knowledge.slice(0, 8)" :key="item.id" class="knowledge-item">
              <strong>{{ item.title }}</strong>
              <p>{{ item.content }}</p>
            </article>
          </div>
          <n-empty v-else description="还没有知识条目" />
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import Graph from 'graphology'
import Sigma from 'sigma'
import {
  NAlert,
  NButton,
  NEmpty,
  NForm,
  NFormItem,
  NInput,
  useMessage,
} from 'naive-ui'
import { p3394Api } from '../api'

const workflowId = 'p3394_runtime_agent'
const message = useMessage()
const graphEl = ref(null)
const renderer = ref(null)
const sigmaGraph = ref(null)
const loading = ref(false)
const seeding = ref(false)
const savingRelation = ref(false)
const savingKnowledge = ref(false)
const generatingDailyMemory = ref(false)
const error = ref('')
const graph = ref({ node_count: 0, edge_count: 0, nodes: [], edges: [] })
const knowledge = ref([])
const dailyNotes = ref([])
const timelineDays = ref(7)
const searchText = ref('')
const selectedNodeId = ref('')
const hoveredNodeId = ref('')
const viewMode = ref('cluster')

const viewModes = [
  { label: '分群视图', value: 'cluster' },
  { label: '核心视图', value: 'core' },
  { label: '关系视图', value: 'relation' },
]

const coreNodeLabels = [
  '你',
  'P3394 Agent Platform',
  'P3394 Runtime Agent',
  'AgentClaw',
  '记忆图谱',
  'SQLite 本地记忆库',
]

const relationForm = reactive({
  source_label: '',
  relation: 'related_to',
  target_label: '',
  evidence: '',
})

const knowledgeForm = reactive({
  title: '',
  content: '',
})

const kindPalette = {
  person: '#0f766e',
  project: '#2563eb',
  agent: '#334155',
  runtime: '#7c3aed',
  database: '#ea580c',
  document: '#0891b2',
  tool: '#be123c',
  capability: '#16a34a',
  process: '#ca8a04',
  model: '#9333ea',
  knowledge: '#64748b',
  memory_bucket: '#0f766e',
  daily_memory: '#0369a1',
  daily_note: '#0284c7',
  memory_category: '#4f46e5',
  concept: '#64748b',
}

const kindLabels = {
  person: '人物',
  project: '项目',
  agent: '智能体',
  runtime: '运行时',
  database: '数据库',
  document: '文档',
  tool: '工具',
  capability: '能力',
  process: '流程',
  model: '模型',
  knowledge: '知识',
  memory_bucket: '记忆桶',
  daily_memory: '每日记忆',
  daily_note: '日记',
  memory_category: '记忆分类',
  concept: '概念',
}

const kindCenters = {
  person: { x: -5.4, y: 0.4 },
  project: { x: -2.5, y: -2.7 },
  agent: { x: 1.1, y: -2.3 },
  capability: { x: 4.7, y: -0.4 },
  tool: { x: 3.8, y: 2.6 },
  document: { x: -1.3, y: 3.3 },
  database: { x: 1.7, y: 3.0 },
  runtime: { x: -4.4, y: -2.3 },
  process: { x: 5.3, y: 2.1 },
  model: { x: -5.2, y: 2.5 },
  daily_memory: { x: -3.7, y: 3.7 },
  daily_note: { x: -5.5, y: 4.5 },
  memory_category: { x: -6.5, y: 1.2 },
  concept: { x: 0, y: 0 },
}

const legendItems = computed(() => {
  const kinds = new Set((graph.value.nodes || []).map(node => node.kind || 'concept'))
  return Array.from(kinds).sort().map(kind => ({
    kind,
    label: kindLabel(kind),
    color: kindColor(kind),
  }))
})

const hasGraph = computed(() => (graph.value.nodes || []).length > 0)

const nodeDegree = computed(() => {
  const degree = new Map()
  for (const node of graph.value.nodes || []) {
    degree.set(node.id, 0)
  }
  for (const edge of graph.value.edges || []) {
    degree.set(edge.source_node_id, (degree.get(edge.source_node_id) || 0) + 1)
    degree.set(edge.target_node_id, (degree.get(edge.target_node_id) || 0) + 1)
  }
  return degree
})

const enrichedNodes = computed(() => (graph.value.nodes || []).map(node => ({
  ...node,
  degree: nodeDegree.value.get(node.id) || 0,
})))

const selectedNode = computed(() => enrichedNodes.value.find(node => node.id === selectedNodeId.value) || null)

const selectedRelations = computed(() => {
  if (!selectedNodeId.value) return []
  return (graph.value.edges || [])
    .filter(edge => edge.source_node_id === selectedNodeId.value || edge.target_node_id === selectedNodeId.value)
    .slice(0, 10)
})

const filteredNodes = computed(() => {
  const query = searchText.value.trim().toLowerCase()
  const nodes = enrichedNodes.value
  if (!query) return nodes.slice().sort((a, b) => b.degree - a.degree)
  return nodes
    .filter(node => {
      const nodeText = `${node.label} ${node.kind} ${node.summary || ''}`.toLowerCase()
      const relationText = (graph.value.edges || [])
        .filter(edge => edge.source_node_id === node.id || edge.target_node_id === node.id)
        .map(edge => `${edge.relation} ${edge.evidence || ''} ${edge.source_label || ''} ${edge.target_label || ''}`)
        .join(' ')
        .toLowerCase()
      return nodeText.includes(query) || relationText.includes(query)
    })
    .sort((a, b) => b.degree - a.degree)
})

function kindColor(kind = 'concept') {
  return kindPalette[kind] || kindPalette.concept
}

function kindLabel(kind = 'concept') {
  return kindLabels[kind] || kind
}

function getNodeSize(node) {
  const degree = nodeDegree.value.get(node.id) || 0
  return Math.min(22, 7 + degree * 1.8)
}

function getNodePosition(index, total) {
  const node = enrichedNodes.value[index]
  if (viewMode.value === 'core') return getCoreNodePosition(node, index, total)
  if (viewMode.value === 'relation') return getRelationNodePosition(node, index, total)
  return getClusteredNodePosition(node, index, total)
}

function getClusteredNodePosition(node, index, total) {
  const center = kindCenters[node?.kind || 'concept'] || kindCenters.concept
  const sameKindNodes = enrichedNodes.value.filter(item => (item.kind || 'concept') === (node?.kind || 'concept'))
  const localIndex = Math.max(0, sameKindNodes.findIndex(item => item.id === node.id))
  const angle = localIndex * Math.PI * (3 - Math.sqrt(5))
  const radius = 0.35 + Math.sqrt(localIndex + 1) * 0.58
  return {
    x: center.x + Math.cos(angle) * radius,
    y: center.y + Math.sin(angle) * radius,
  }
}

function getCoreNodePosition(node, index, total) {
  const coreIndex = coreNodeLabels.findIndex(label => label === node?.label)
  if (coreIndex >= 0) {
    const angle = (Math.PI * 2 * coreIndex) / coreNodeLabels.length - Math.PI / 2
    const radius = coreIndex === 0 ? 0 : 2.2
    return {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    }
  }
  const nearestCoreIndex = index % coreNodeLabels.length
  const angle = (Math.PI * 2 * nearestCoreIndex) / coreNodeLabels.length - Math.PI / 2
  const ring = 3.7 + (index % 5) * 0.55
  return {
    x: Math.cos(angle) * ring + Math.cos(index * 1.7) * 0.9,
    y: Math.sin(angle) * ring + Math.sin(index * 1.7) * 0.9,
  }
}

function getRelationNodePosition(node, index, total) {
  const degree = nodeDegree.value.get(node?.id) || 0
  const maxDegree = Math.max(1, ...Array.from(nodeDegree.value.values()))
  const normalized = 1 - degree / maxDegree
  const angle = index * Math.PI * (3 - Math.sqrt(5))
  const radius = 0.75 + normalized * 6.8 + (index % 4) * 0.22
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
  }
}

function getGoldenNodePosition(index, total) {
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  const radius = 0.55 + Math.sqrt(index + 1) / Math.sqrt(Math.max(total, 1)) * 8
  return {
    x: Math.cos(index * goldenAngle) * radius,
    y: Math.sin(index * goldenAngle) * radius,
  }
}

function relationColor(edge) {
  if (edge.relation === 'owns') return '#0f766e'
  if (edge.relation === 'runs_on') return '#2563eb'
  if (edge.relation === 'stores_memory_in') return '#ea580c'
  if (edge.relation === 'uses') return '#9333ea'
  if (edge.relation === 'reads') return '#0891b2'
  return '#94a3b8'
}

function buildSigmaGraph() {
  const network = new Graph({ multi: true, type: 'directed' })
  const nodes = enrichedNodes.value
  nodes.forEach((node, index) => {
    const position = getNodePosition(index, nodes.length)
    network.addNode(node.id, {
      label: node.label,
      kind: node.kind,
      summary: node.summary || '',
      x: position.x,
      y: position.y,
      size: getNodeSize(node),
      color: kindColor(node.kind),
      degree: node.degree,
    })
  })
  ;(graph.value.edges || []).forEach(edge => {
    if (!network.hasNode(edge.source_node_id) || !network.hasNode(edge.target_node_id)) return
    const key = edge.id || `${edge.source_node_id}-${edge.relation}-${edge.target_node_id}`
    if (network.hasEdge(key)) return
    network.addDirectedEdgeWithKey(key, edge.source_node_id, edge.target_node_id, {
      label: edge.relation,
      relation: edge.relation,
      evidence: edge.evidence || '',
      source_label: edge.source_label || '',
      target_label: edge.target_label || '',
      color: relationColor(edge),
      size: Math.max(1, Math.min(4, Number(edge.weight || 1))),
    })
  })
  return network
}

function disposeRenderer() {
  if (renderer.value) {
    renderer.value.kill()
    renderer.value = null
  }
  sigmaGraph.value = null
}

function renderGraph() {
  if (!graphEl.value) return
  disposeRenderer()
  const network = buildSigmaGraph()
  sigmaGraph.value = network
  renderer.value = new Sigma(network, graphEl.value, {
    allowInvalidContainer: true,
    defaultNodeType: 'circle',
    defaultEdgeType: 'arrow',
    labelColor: { color: '#0f172a' },
    labelDensity: 0.08,
    labelGridCellSize: 80,
    labelRenderedSizeThreshold: 8,
    edgeLabelSize: 11,
    minCameraRatio: 0.08,
    maxCameraRatio: 3,
    renderEdgeLabels: true,
  })
  renderer.value.on('clickNode', ({ node }) => selectNode(node, false))
  renderer.value.on('enterNode', ({ node }) => {
    hoveredNodeId.value = node
    renderer.value.refresh()
  })
  renderer.value.on('leaveNode', () => {
    hoveredNodeId.value = ''
    renderer.value.refresh()
  })
  renderer.value.setSetting('nodeReducer', (node, data) => nodeReducer(node, data))
  renderer.value.setSetting('edgeReducer', (edge, data) => edgeReducer(edge, data))
  if (!selectedNodeId.value && enrichedNodes.value.length) {
    selectedNodeId.value = enrichedNodes.value.slice().sort((a, b) => b.degree - a.degree)[0].id
  }
}

function nodeReducer(node, data) {
  const focus = selectedNodeId.value || hoveredNodeId.value
  const query = searchText.value.trim().toLowerCase()
  const result = { ...data }
  const network = sigmaGraph.value
  if (query) {
    const text = `${data.label} ${data.kind} ${data.summary || ''}`.toLowerCase()
    if (!text.includes(query)) {
      result.color = '#cbd5e1'
      result.label = ''
    }
  }
  if (focus && network?.hasNode(focus)) {
    const isNeighbor = node === focus || network.areNeighbors(node, focus)
    if (!isNeighbor) {
      result.color = '#d8dee8'
      result.label = ''
      result.size = Math.max(3, data.size * 0.55)
    } else {
      result.highlighted = node === focus
    }
  }
  return result
}

function edgeReducer(edge, data) {
  const focus = selectedNodeId.value || hoveredNodeId.value
  const result = { ...data }
  const network = sigmaGraph.value
  if (focus && network?.hasEdge(edge)) {
    const [source, target] = network.extremities(edge)
    if (source !== focus && target !== focus) {
      result.hidden = true
    } else {
      result.size = Math.max(2, data.size || 1)
    }
  }
  return result
}

function selectNode(nodeId, animate = true) {
  selectedNodeId.value = nodeId
  renderer.value?.refresh()
  if (!animate || !renderer.value || !sigmaGraph.value?.hasNode(nodeId)) return
  const attrs = sigmaGraph.value.getNodeAttributes(nodeId)
  renderer.value.getCamera().animate(
    { x: attrs.x, y: attrs.y, ratio: 0.35 },
    { duration: 420 },
  )
}

function resetCamera() {
  selectedNodeId.value = ''
  hoveredNodeId.value = ''
  renderer.value?.refresh()
  renderer.value?.getCamera().animatedReset({ duration: 420 })
}

function setViewMode(mode) {
  viewMode.value = mode
  selectedNodeId.value = ''
  nextTick(() => renderGraph())
}

function focusFirstMatch() {
  const first = filteredNodes.value[0]
  if (first) selectNode(first.id, true)
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [graphResponse, knowledgeResponse, dailyMemoryResponse] = await Promise.all([
      p3394Api.memoryGraph({ workflow_id: workflowId, limit: 500 }),
      p3394Api.knowledge({ workflow_id: workflowId, limit: 80 }),
      p3394Api.dailyMemoryTimeline({ workflow_id: workflowId, days: timelineDays.value }),
    ])
    graph.value = graphResponse
    knowledge.value = knowledgeResponse.items || []
    dailyNotes.value = dailyMemoryResponse.notes || []
    await nextTick()
    renderGraph()
  } catch (err) {
    error.value = err.response?.data?.detail?.error || err.response?.data?.error || err.message || '记忆图谱加载失败'
  } finally {
    loading.value = false
  }
}

async function setTimelineDays(days) {
  timelineDays.value = days
  await loadAll()
}

function focusDailyNote(note) {
  if (!note?.date_key) return
  searchText.value = note.date_key
  nextTick(() => {
    const node = enrichedNodes.value.find(item => item.label === note.date_key)
    if (node) selectNode(node.id, true)
  })
}

async function generateTodayMemory() {
  generatingDailyMemory.value = true
  error.value = ''
  try {
    await p3394Api.generateDailyMemory({
      title: '今日生成',
      content: '手动生成今日 P3394 每日记忆文件，用于本地知识库和记忆图谱索引。',
      tags: ['daily-memory', 'manual-checkpoint'],
    }, { workflow_id: workflowId })
    message.success('今日记忆已生成')
    await loadAll()
  } catch (err) {
    error.value = err.response?.data?.detail?.error || err.response?.data?.error || err.message || '今日记忆生成失败'
  } finally {
    generatingDailyMemory.value = false
  }
}

async function seedDemo() {
  seeding.value = true
  error.value = ''
  try {
    await p3394Api.seedMemoryGraph({ workflow_id: workflowId })
    message.success('大型示例图已生成')
    await loadAll()
  } catch (err) {
    error.value = err.response?.data?.detail?.error || err.response?.data?.error || err.message || '大型示例图生成失败'
  } finally {
    seeding.value = false
  }
}

async function saveRelation() {
  if (!relationForm.source_label.trim() || !relationForm.target_label.trim()) {
    message.warning('请填写源节点和目标节点')
    return
  }
  savingRelation.value = true
  try {
    await p3394Api.createMemoryRelation({
      workflow_id: workflowId,
      ...relationForm,
    })
    relationForm.source_label = ''
    relationForm.target_label = ''
    relationForm.relation = 'related_to'
    relationForm.evidence = ''
    message.success('关系已保存')
    await loadAll()
  } catch (err) {
    error.value = err.response?.data?.detail?.error || err.response?.data?.error || err.message || '关系保存失败'
  } finally {
    savingRelation.value = false
  }
}

async function saveKnowledge() {
  if (!knowledgeForm.title.trim() || !knowledgeForm.content.trim()) {
    message.warning('请填写标题和内容')
    return
  }
  savingKnowledge.value = true
  try {
    await p3394Api.createKnowledge({
      workflow_id: workflowId,
      title: knowledgeForm.title,
      content: knowledgeForm.content,
      source: 'memory_graph_page',
      tags: ['memory-graph', 'sigma'],
    })
    knowledgeForm.title = ''
    knowledgeForm.content = ''
    message.success('知识已保存')
    await loadAll()
  } catch (err) {
    error.value = err.response?.data?.detail?.error || err.response?.data?.error || err.message || '知识保存失败'
  } finally {
    savingKnowledge.value = false
  }
}

watch(searchText, () => renderer.value?.refresh())

watch(viewMode, () => renderer.value?.refresh())

watch(graphEl, () => {
  if (graphEl.value) renderGraph()
})

onMounted(loadAll)

onBeforeUnmount(disposeRenderer)
</script>

<style scoped>
.memory-page {
  min-height: calc(100vh - 48px);
}

.memory-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.eyebrow {
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.memory-header h1 {
  margin: 0;
  color: #0f172a;
  font-size: 30px;
  line-height: 1.16;
}

.memory-header p {
  max-width: 760px;
  margin: 8px 0 0;
  color: #64748b;
}

.header-actions,
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.memory-alert {
  margin-bottom: 16px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.stat {
  min-height: 76px;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #ffffff;
  padding: 13px 14px;
}

.stat span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.stat strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 22px;
  line-height: 1.2;
}

.memory-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 370px;
  gap: 14px;
  align-items: start;
}

.atlas-panel,
.inspector-section {
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #ffffff;
}

.atlas-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #e5edf7;
  padding: 12px;
}

.atlas-search {
  max-width: 420px;
}

.graph-shell {
  position: relative;
  min-height: 700px;
  overflow: hidden;
  background:
    radial-gradient(circle at 18% 20%, rgba(37, 99, 235, 0.08), transparent 28%),
    radial-gradient(circle at 75% 10%, rgba(15, 118, 110, 0.06), transparent 24%),
    linear-gradient(rgba(15, 23, 42, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.045) 1px, transparent 1px),
    #f8fafc;
  background-size: auto, auto, 30px 30px, 30px 30px, auto;
}

.graph-canvas {
  width: 100%;
  height: 700px;
}

.graph-overlay {
  position: absolute;
  right: 12px;
  bottom: 12px;
  display: flex;
  max-width: 72%;
  flex-wrap: wrap;
  gap: 6px;
  pointer-events: none;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: #334155;
  font-size: 12px;
  padding: 4px 8px;
}

.legend-dot,
.node-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 999px;
}

.empty-graph {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  text-align: center;
}

.empty-graph h2 {
  margin: 0 0 8px;
  font-size: 18px;
}

.empty-graph p {
  color: #64748b;
}

.inspector-panel {
  display: grid;
  gap: 12px;
}

.inspector-section {
  padding: 14px;
}

.section-title {
  margin-bottom: 10px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.section-header .section-title {
  margin-bottom: 0;
}

.daily-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.selected-node h2 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 20px;
}

.selected-node p,
.relation-item p,
.knowledge-item p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.node-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.node-meta span {
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  padding: 3px 8px;
}

.node-list,
.relation-list,
.knowledge-list,
.daily-note-list {
  display: grid;
  gap: 8px;
  max-height: 300px;
  overflow: auto;
}

.daily-note-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  padding: 10px;
  transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}

.daily-note-item:hover,
.daily-note-item.active {
  border-color: #7dd3fc;
  background: #f0f9ff;
}

.daily-note-item:active {
  transform: translateY(1px);
}

.daily-note-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #0f172a;
  font-size: 13px;
}

.daily-note-head span,
.daily-note-path {
  color: #64748b;
  font-size: 12px;
}

.daily-note-path {
  margin: 5px 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.daily-note-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 7px;
}

.daily-note-tags span {
  max-width: 100%;
  overflow: hidden;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 11px;
  padding: 2px 6px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.daily-note-item pre {
  max-height: 150px;
  margin: 0;
  overflow: auto;
  border-radius: 6px;
  background: #ffffff;
  color: #334155;
  font-size: 11px;
  line-height: 1.5;
  padding: 8px;
  white-space: pre-wrap;
}

.node-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  width: 100%;
  gap: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  color: #0f172a;
  cursor: pointer;
  font: inherit;
  padding: 8px 10px;
  text-align: left;
  transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}

.node-row:hover,
.node-row.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.node-row:active {
  transform: translateY(1px);
}

.node-row span:nth-child(2) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-row small {
  color: #64748b;
}

.relation-item,
.knowledge-item {
  border-top: 1px solid #eef2f7;
  padding-top: 8px;
}

.relation-item:first-child,
.knowledge-item:first-child {
  border-top: 0;
  padding-top: 0;
}

.relation-item strong,
.knowledge-item strong {
  display: block;
  margin-bottom: 4px;
  color: #0f172a;
  font-size: 13px;
}

.knowledge-item p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

@media (max-width: 1180px) {
  .memory-workbench {
    grid-template-columns: 1fr;
  }

  .inspector-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .memory-header,
  .atlas-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .stats-row,
  .inspector-panel {
    grid-template-columns: 1fr;
  }

  .atlas-search {
    max-width: none;
  }

  .graph-shell {
    min-height: 560px;
  }

  .graph-canvas {
    height: 560px;
  }
}
</style>
