<template>
  <div class="p3394-agent-page" :class="{ 'is-ready': registered }">
    <n-spin :show="loading">
      <n-alert v-if="loadError" type="error" class="alert">
        {{ loadError }}
      </n-alert>

      <AgentChat
        v-if="registered"
        :workflow-id="workflowId"
        :assistant-name="brand.primaryAgentName"
        assistant-initials="P"
        class="p3394-chat-main"
      />

      <aside
        v-if="registered"
        class="p3394-workbench"
        :class="{ 'workbench-collapsed': workbenchCollapsed }"
        aria-label="P3394 工作台"
      >
        <nav class="workbench-rail" aria-label="P3394 工具">
          <button
            class="rail-button rail-toggle"
            type="button"
            :title="workbenchCollapsed ? '打开工作台' : '收起工作台'"
            @click="workbenchCollapsed = !workbenchCollapsed"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path :d="workbenchCollapsed ? 'M9 18l6-6-6-6' : 'M15 18l-6-6 6-6'" />
            </svg>
          </button>
          <button
            v-for="tab in workbenchTabs"
            :key="tab.key"
            class="rail-button"
            :class="{ active: activeWorkbenchTab === tab.key && !workbenchCollapsed }"
            type="button"
            :title="tab.label"
            @click="openWorkbenchTab(tab.key)"
          >
            <span class="rail-label">{{ tab.short }}</span>
            <span v-if="tab.count" class="rail-count">{{ tab.count }}</span>
          </button>
        </nav>

        <div v-if="!workbenchCollapsed" class="workbench-panel">
          <div class="workbench-header">
            <div>
              <div class="workbench-title">{{ activeWorkbenchLabel }}</div>
              <div class="workbench-meta">P3394 Runtime</div>
            </div>
            <n-button size="tiny" quaternary :loading="workbenchLoading" @click="loadWorkbench">刷新</n-button>
          </div>

          <div class="workbench-tabs" role="tablist" aria-label="P3394 工作台标签">
            <button
              v-for="tab in workbenchTabs"
              :key="`panel-${tab.key}`"
              class="tab-button"
              :class="{ active: activeWorkbenchTab === tab.key }"
              type="button"
              @click="activeWorkbenchTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>

          <section v-if="activeWorkbenchTab === 'artifacts'" class="workbench-section">
            <div class="section-heading">
              <span>文件产物</span>
              <n-tag size="tiny" :bordered="false">{{ artifacts.length }}</n-tag>
            </div>
            <div v-if="!artifacts.length" class="empty-line">还没有生成文件</div>
            <div v-else class="artifact-list">
              <article v-for="artifact in artifacts" :key="artifact.id || artifact.path" class="artifact-item">
                <div class="item-title-row">
                  <span class="item-name">{{ artifact.display_name || artifact.path }}</span>
                  <n-tag size="tiny" :bordered="false">{{ artifact.file_type || 'file' }}</n-tag>
                </div>
                <div class="item-path">{{ artifact.path }}</div>
                <div class="item-actions">
                  <n-button v-if="artifact.path" size="tiny" text @click="openArtifactPath(artifact.path)">打开</n-button>
                  <n-button v-if="artifact.path" size="tiny" text @click="copyText(artifact.path)">复制路径</n-button>
                  <span>{{ formatBytes(artifact.size) }}</span>
                </div>
                <pre v-if="artifact.file_type === 'run_log'" class="log-preview">{{ artifact.preview }}</pre>
              </article>
            </div>
          </section>

          <section v-if="activeWorkbenchTab === 'knowledge'" class="workbench-section">
            <div class="section-heading">
              <span>本地知识库</span>
              <n-tag size="tiny" :bordered="false">{{ knowledgeItems.length }}</n-tag>
            </div>
            <n-input
              v-model:value="knowledgeImportPath"
              size="small"
              placeholder="输入文件或文件夹路径"
              clearable
            />
            <div
              class="drop-zone"
              :class="{ dragging: knowledgeDragging }"
              @dragover.prevent="knowledgeDragging = true"
              @dragleave.prevent="knowledgeDragging = false"
              @drop.prevent="dropKnowledgeFiles"
            >
              <div>拖入文件</div>
              <small>md / pdf / docx / txt</small>
            </div>
            <div class="knowledge-actions">
              <n-checkbox v-model:checked="knowledgeImportRecursive" size="small">递归</n-checkbox>
              <input
                ref="knowledgeFileInput"
                class="hidden-input"
                type="file"
                multiple
                accept=".md,.markdown,.pdf,.doc,.docx,.txt,.log,.json,.yaml,.yml,.csv"
                @change="chooseKnowledgeFiles"
              />
              <input
                ref="knowledgeFolderInput"
                class="hidden-input"
                type="file"
                webkitdirectory
                directory
                multiple
                @change="chooseKnowledgeFiles"
              />
              <n-button size="small" secondary @click="knowledgeFileInput?.click()">选文件</n-button>
              <n-button size="small" secondary @click="knowledgeFolderInput?.click()">选文件夹</n-button>
              <n-button
                size="small"
                type="primary"
                :loading="knowledgeImporting"
                :disabled="!knowledgeImportPath.trim()"
                @click="importKnowledge"
              >
                导入
              </n-button>
            </div>
            <div v-if="!knowledgeItems.length" class="empty-line">可导入 md/pdf/docx/txt</div>
            <div v-else class="knowledge-list">
              <div v-for="item in knowledgeItems.slice(0, 4)" :key="item.id" class="knowledge-item">
                <div>
                  <span>{{ item.title }}</span>
                  <small>{{ item.metadata?.summary || item.source }}</small>
                </div>
              </div>
            </div>
          </section>

          <section v-if="activeWorkbenchTab === 'execution'" class="workbench-section">
            <div class="section-heading">
              <span>执行记录</span>
              <n-tag size="tiny" :bordered="false">{{ executionSummaries.length }}</n-tag>
            </div>
            <div v-if="!executionSummaries.length" class="empty-line">暂无执行记录</div>
            <div v-else class="execution-list">
              <article v-for="record in executionSummaries" :key="record.id" class="execution-item">
                <div class="item-title-row">
                  <span class="item-name">{{ record.request || 'P3394 run' }}</span>
                  <n-tag size="tiny" :type="record.status === 'failed' ? 'error' : 'success'" :bordered="false">
                    {{ record.status || 'unknown' }}
                  </n-tag>
                </div>
                <div class="route-line">{{ record.route_label || 'runtime route' }}</div>
                <div class="step-row">
                  <span>{{ record.tool_count }} 工具</span>
                  <span>{{ record.artifact_count }} 文件</span>
                  <span>{{ formatTime(record.updated_at) }}</span>
                </div>
                <div class="step-list">
                  <div v-for="step in record.steps.slice(0, 5)" :key="`${record.id}-${step.kind}-${step.title}`" class="step-item">
                    <span class="step-kind" :class="`kind-${step.kind}`">{{ readStepLabel(step.kind) }}</span>
                    <span>{{ step.summary || step.title }}</span>
                  </div>
                </div>
              </article>
            </div>
          </section>

          <n-alert v-if="workbenchError" type="error" size="small" class="workbench-error">
            {{ workbenchError }}
          </n-alert>
        </div>
      </aside>

      <section v-else class="p3394-setup">
        <n-card class="p3394-card" :bordered="true">
          <template #header>
            <div class="card-header">
              <div class="avatar">P</div>
              <div>
                <div class="title">{{ brand.productNameZh }}</div>
                <div class="subtitle">你的默认主智能体，基于 AgentClaw 运行时</div>
              </div>
            </div>
          </template>

          <p class="description">
            首次使用需要把内置 P3394 模板注册到当前工作区。启用后会直接进入原生聊天界面，可以接入模型对话、运行命令、搜索资料、分析文档和处理项目文件。
          </p>

          <div class="tag-row">
            <n-tag size="small" :bordered="false">P3394</n-tag>
            <n-tag size="small" :bordered="false">模型</n-tag>
            <n-tag size="small" :bordered="false">命令</n-tag>
            <n-tag size="small" :bordered="false">搜索</n-tag>
            <n-tag size="small" :bordered="false">文档</n-tag>
          </div>

          <div class="actions">
            <n-button
              v-if="needsRepair"
              type="primary"
              :loading="repairing"
              :disabled="!templateAvailable"
              @click="repairAndOpen"
            >
              修复并打开
            </n-button>
            <n-button
              v-else
              type="primary"
              :loading="importing"
              :disabled="!templateAvailable"
              @click="importAndOpen"
            >
              {{ templateAvailable ? '启用 P3394 主智能体' : '模板未找到' }}
            </n-button>
            <n-button size="small" @click="fetchStatus">{{ t('common.refresh') }}</n-button>
          </div>
        </n-card>
      </section>
    </n-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { NAlert, NButton, NCard, NCheckbox, NInput, NSpin, NTag, useMessage } from 'naive-ui'
import AgentChat from './AgentChat.vue'
import { p3394Api, templateLibraryApi, workflowsApi } from '../api'
import { brand } from '../config/brand'

const workflowId = 'p3394_runtime_agent'
const { t } = useI18n()
const message = useMessage()

const loading = ref(false)
const importing = ref(false)
const repairing = ref(false)
const templateAvailable = ref(false)
const imported = ref(false)
const registered = ref(false)
const needsRepair = ref(false)
const loadError = ref('')
const workbenchLoading = ref(false)
const workbenchError = ref('')
const artifacts = ref([])
const knowledgeItems = ref([])
const executionSummaries = ref([])
const knowledgeImportPath = ref('')
const knowledgeImportRecursive = ref(true)
const knowledgeImporting = ref(false)
const knowledgeDragging = ref(false)
const knowledgeFileInput = ref(null)
const knowledgeFolderInput = ref(null)
const workbenchCollapsed = ref(true)
const activeWorkbenchTab = ref('artifacts')

const workbenchTabs = computed(() => [
  { key: 'artifacts', label: '文件产物', short: '文', count: artifacts.value.length },
  { key: 'knowledge', label: '本地知识库', short: '知', count: knowledgeItems.value.length },
  { key: 'execution', label: '执行记录', short: '记', count: executionSummaries.value.length },
])

const activeWorkbenchLabel = computed(() => {
  return workbenchTabs.value.find(tab => tab.key === activeWorkbenchTab.value)?.label || '工作台'
})

function openWorkbenchTab(tab) {
  activeWorkbenchTab.value = tab
  workbenchCollapsed.value = false
}

function applyAppStatus(app) {
  templateAvailable.value = Boolean(app)
  imported.value = Boolean(app?.imported)
  registered.value = Boolean(app?.registered)
  needsRepair.value = Boolean(app?.imported && !app?.registered)
}

async function fetchStatus() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await templateLibraryApi.list()
    const apps = response.apps || []
    applyAppStatus(apps.find(app => app.id === workflowId))
    if (registered.value) await loadWorkbench()
  } catch (error) {
    loadError.value = error.response?.data?.error || 'P3394 状态加载失败'
  } finally {
    loading.value = false
  }
}

function formatBytes(size) {
  if (!size && size !== 0) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(value) {
  if (!value) return '-'
  const date = new Date(Number(value))
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text || '')
    message.success('已复制')
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = text || ''
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    message.success('已复制')
  }
}

async function openArtifactPath(path) {
  if (!path) return
  try {
    const result = await p3394Api.openPath({ path })
    if (result.success) message.success('已打开路径')
    else workbenchError.value = result.error || '打开路径失败'
  } catch (error) {
    workbenchError.value = error.response?.data?.detail?.error || error.response?.data?.error || '打开路径失败'
  }
}

async function loadWorkbench() {
  workbenchLoading.value = true
  workbenchError.value = ''
  try {
    const params = { workflow_id: workflowId, limit: 20 }
    const [artifactResponse, knowledgeResponse, summaryResponse] = await Promise.all([
      p3394Api.artifacts(params),
      p3394Api.knowledge(params),
      p3394Api.executionSummary(params),
    ])
    artifacts.value = artifactResponse.artifacts || []
    knowledgeItems.value = knowledgeResponse.items || []
    executionSummaries.value = summaryResponse.records || []
  } catch (error) {
    workbenchError.value = error.response?.data?.detail?.error || error.response?.data?.error || 'P3394 工作台加载失败'
  } finally {
    workbenchLoading.value = false
  }
}

async function importKnowledge() {
  const raw = knowledgeImportPath.value.trim()
  if (!raw) return
  knowledgeImporting.value = true
  workbenchError.value = ''
  try {
    const result = await p3394Api.importKnowledge({
      workflow_id: workflowId,
      paths: [raw],
      recursive: knowledgeImportRecursive.value,
      max_files: 80,
    })
    message.success(`已导入 ${result.imported_count || 0} 个文件`)
    knowledgeImportPath.value = ''
    await loadWorkbench()
  } catch (error) {
    workbenchError.value = error.response?.data?.detail?.error || error.response?.data?.error || '知识库导入失败'
  } finally {
    knowledgeImporting.value = false
  }
}

async function importKnowledgeFileList(fileList) {
  const files = Array.from(fileList || [])
  if (!files.length) return
  knowledgeImporting.value = true
  workbenchError.value = ''
  try {
    const form = new FormData()
    form.append('workflow_id', workflowId)
    form.append('recursive', String(knowledgeImportRecursive.value))
    for (const file of files) form.append('files', file)
    const result = await p3394Api.importKnowledgeFiles(form)
    message.success(`已导入 ${result.imported_count || 0} 个文件`)
    await loadWorkbench()
  } catch (error) {
    workbenchError.value = error.response?.data?.detail?.error || error.response?.data?.error || '知识库导入失败'
  } finally {
    knowledgeImporting.value = false
    knowledgeDragging.value = false
    if (knowledgeFileInput.value) knowledgeFileInput.value.value = ''
    if (knowledgeFolderInput.value) knowledgeFolderInput.value.value = ''
  }
}

function chooseKnowledgeFiles(event) {
  importKnowledgeFileList(event.target.files)
}

function dropKnowledgeFiles(event) {
  knowledgeDragging.value = false
  importKnowledgeFileList(event.dataTransfer?.files)
}

function readStepLabel(kind) {
  return {
    route: '路由',
    role: '角色',
    read: '读取',
    run: '命令',
    write: '写入',
    verify: '验证',
    log: '日志',
  }[kind] || kind
}

async function waitForWorkflowReady() {
  const delays = [120, 240, 500, 900]
  let lastError = null
  for (const delay of delays) {
    try {
      await workflowsApi.get(workflowId)
      return
    } catch (error) {
      lastError = error
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
  if (lastError) throw lastError
}

async function importAndOpen() {
  importing.value = true
  loadError.value = ''
  try {
    const result = await templateLibraryApi.importApp(workflowId, { overwrite: false })
    imported.value = Boolean(result.imported)
    registered.value = Boolean(result.registered)
    needsRepair.value = imported.value && !registered.value
    if (registered.value) await waitForWorkflowReady()
    message.success(result.message || 'P3394 Agent 已启用')
  } catch (error) {
    loadError.value = error.response?.data?.error || 'P3394 Agent 启用失败'
  } finally {
    importing.value = false
  }
}

async function repairAndOpen() {
  repairing.value = true
  loadError.value = ''
  try {
    const result = await templateLibraryApi.repairApp(workflowId)
    imported.value = Boolean(result.imported)
    registered.value = Boolean(result.registered)
    needsRepair.value = imported.value && !registered.value
    if (registered.value) await waitForWorkflowReady()
    message.success(result.message || 'P3394 Agent 已修复')
  } catch (error) {
    loadError.value = error.response?.data?.error || 'P3394 Agent 修复失败'
  } finally {
    repairing.value = false
  }
}

onMounted(fetchStatus)

watch(registered, (value) => {
  if (value) loadWorkbench()
})
</script>

<style scoped>
.p3394-agent-page {
  display: flex;
  min-height: 100%;
}

.p3394-agent-page.is-ready {
  height: 100vh;
  min-height: 100vh;
  margin: -24px;
  width: calc(100% + 48px);
  overflow: hidden;
}

.p3394-agent-page.is-ready :deep(.n-spin-container),
.p3394-agent-page.is-ready :deep(.n-spin-content) {
  display: flex;
  width: 100%;
  min-height: 100vh;
  height: 100vh;
  overflow: hidden;
}

.alert {
  margin-bottom: 16px;
}

.p3394-agent-page.is-ready .alert {
  margin: 16px;
}

.p3394-chat-main {
  flex: 1 1 auto;
  min-width: 0;
}

.p3394-agent-page.is-ready :deep(.agent-chat) {
  height: 100vh;
  margin: 0;
  width: 100%;
}

.p3394-workbench {
  width: 364px;
  min-width: 364px;
  height: 100vh;
  overflow: hidden;
  border-left: 1px solid #e5e7eb;
  background: #f8fafc;
  display: flex;
  transition: width 0.18s ease, min-width 0.18s ease;
}

.p3394-workbench.workbench-collapsed {
  width: 52px;
  min-width: 52px;
}

.workbench-rail {
  width: 52px;
  flex: 0 0 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  border-right: 1px solid #e5e7eb;
  background: #ffffff;
}

.rail-button {
  position: relative;
  width: 34px;
  height: 34px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease, transform 0.12s ease;
}

.rail-button:hover,
.rail-button.active {
  border-color: #dbe3ec;
  background: #f1f5f9;
  color: #111827;
}

.rail-button:active {
  transform: translateY(1px);
}

.rail-button svg {
  width: 16px;
  height: 16px;
}

.rail-toggle {
  margin-bottom: 4px;
}

.rail-count {
  position: absolute;
  right: -4px;
  top: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border: 1px solid #ffffff;
  border-radius: 999px;
  background: #0f766e;
  color: #ffffff;
  font-size: 9px;
  line-height: 14px;
  font-weight: 700;
}

.workbench-panel {
  flex: 1;
  min-width: 0;
  height: 100vh;
  overflow-y: auto;
  padding: 14px;
}

.workbench-header,
.section-heading,
.item-title-row,
.knowledge-actions,
.step-row,
.workbench-tabs {
  display: flex;
  align-items: center;
}

.workbench-header {
  justify-content: space-between;
  gap: 12px;
  padding: 4px 2px 12px;
}

.workbench-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.workbench-meta {
  margin-top: 2px;
  font-size: 12px;
  color: #64748b;
}

.workbench-tabs {
  gap: 4px;
  margin: 0 0 12px;
  padding: 3px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.tab-button {
  flex: 1;
  min-width: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  padding: 8px 6px;
  transition: background 0.16s ease, color 0.16s ease;
}

.tab-button:hover,
.tab-button.active {
  background: #f1f5f9;
  color: #111827;
}

.workbench-section {
  padding: 0;
  border-top: 0;
}

.section-heading {
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  color: #111827;
  font-size: 13px;
  font-weight: 700;
}

.empty-line {
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.7;
}

.artifact-list,
.knowledge-list,
.execution-list,
.step-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.artifact-item,
.execution-item {
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
}

.item-title-row {
  justify-content: space-between;
  gap: 8px;
}

.item-name {
  min-width: 0;
  overflow: hidden;
  color: #111827;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-path,
.route-line {
  margin-top: 5px;
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 11px;
  line-height: 1.5;
  word-break: break-all;
}

.item-actions,
.step-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  color: #64748b;
  font-size: 11px;
}

.knowledge-actions {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px;
  margin: 10px 0;
}

.drop-zone {
  margin-top: 10px;
  padding: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  text-align: center;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.drop-zone.dragging {
  border-color: #0f766e;
  background: #f0fdfa;
}

.drop-zone div {
  font-size: 13px;
  font-weight: 650;
}

.drop-zone small {
  display: block;
  margin-top: 2px;
  color: #64748b;
  font-size: 11px;
}

.hidden-input {
  display: none;
}

.knowledge-item {
  display: block;
  padding: 7px 0;
  border-top: 1px solid #eef2f7;
  font-size: 12px;
}

.knowledge-item span {
  display: block;
  color: #111827;
  font-weight: 650;
}

.knowledge-item small {
  display: block;
  margin-top: 2px;
  color: #94a3b8;
  line-height: 1.45;
}

.log-preview {
  max-height: 120px;
  margin: 8px 0 0;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border-radius: 6px;
  background: #0f172a;
  color: #dbeafe;
  padding: 8px;
  font-size: 11px;
  line-height: 1.45;
}

.step-list {
  margin-top: 8px;
  gap: 5px;
}

.step-item {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 6px;
  color: #475569;
  font-size: 11px;
  line-height: 1.5;
}

.step-kind {
  color: #0f766e;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.step-kind.kind-verify {
  color: #166534;
}

.step-kind.kind-write {
  color: #b45309;
}

.step-kind.kind-read {
  color: #1d4ed8;
}

.step-kind.kind-log {
  color: #64748b;
}

.workbench-error {
  margin-top: 12px;
}

.p3394-setup {
  display: flex;
  min-height: calc(100vh - 48px);
  align-items: center;
  justify-content: center;
  padding: 32px 18px;
}

.p3394-card {
  width: min(620px, 100%);
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid #d9dee7;
  border-radius: 8px;
  background: #f3f6f9;
  color: #1f2937;
  font-weight: 700;
}

.title {
  font-weight: 700;
  color: var(--text-primary);
}

.subtitle,
.description {
  color: var(--text-secondary);
}

.description {
  margin: 0 0 14px;
  line-height: 1.7;
}

.tag-row,
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.actions {
  align-items: center;
  margin-top: 20px;
}

@media (max-width: 1180px) {
  .p3394-workbench {
    width: 320px;
    min-width: 320px;
  }

  .p3394-workbench.workbench-collapsed {
    width: 52px;
    min-width: 52px;
  }
}

@media (max-width: 960px) {
  .p3394-agent-page.is-ready,
  .p3394-agent-page.is-ready :deep(.n-spin-container),
  .p3394-agent-page.is-ready :deep(.n-spin-content) {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .p3394-agent-page.is-ready :deep(.n-spin-content) {
    flex-direction: column;
  }

  .p3394-workbench {
    width: 100%;
    min-width: 0;
    height: auto;
    max-height: none;
    border-left: 0;
    border-top: 1px solid #e5e7eb;
    flex-direction: column;
  }

  .p3394-workbench.workbench-collapsed {
    width: 100%;
    min-width: 0;
  }

  .workbench-rail {
    width: 100%;
    flex: 0 0 auto;
    flex-direction: row;
    justify-content: flex-end;
    border-right: 0;
    border-bottom: 1px solid #e5e7eb;
  }

  .workbench-panel {
    height: auto;
    max-height: 50vh;
  }
}
</style>
