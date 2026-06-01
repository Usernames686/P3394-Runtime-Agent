import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('P3394 Agent shell', () => {
  it('exposes model diagnostic endpoints in the admin API client', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/api/index.js'), 'utf8')

    expect(source).toContain("diagnostics: () => api.get('/models/diagnostics')")
    expect(source).toContain("test: (modelId) => api.post(`/models/${modelId}/test`)")
  })

  it('renders P3394 through the native AgentClaw chat layout', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/P3394Agent.vue'), 'utf8')

    expect(source).toContain('<AgentChat')
    expect(source).toContain(':workflow-id="workflowId"')
    expect(source).toContain('p3394-agent-page')
    expect(source).not.toContain('compact')
    expect(source).not.toContain('hide-config-panel')
    expect(source).not.toContain('hide-process-details')
    expect(source).not.toContain('hide-top-bar')
    expect(source).not.toContain('auto-approve-tool-confirmations')
    expect(source).not.toContain('model-health-strip')
    expect(source).not.toContain('runtime-detail-panel')
    expect(source).not.toContain('orchestration-rail')
  })

  it('keeps P3394 setup focused on template registration', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/P3394Agent.vue'), 'utf8')

    expect(source).toContain('templateLibraryApi.list')
    expect(source).toContain('templateLibraryApi.importApp')
    expect(source).toContain('templateLibraryApi.repairApp')
    expect(source).toContain('repairAndOpen')
    expect(source).toContain('修复并打开')
    expect(source).toContain('启用 P3394 主智能体')
    expect(source).not.toContain('modelsApi')
    expect(source).not.toContain('CommandResultCard')
  })

  it('adds a practical P3394 workbench that stays collapsed by default', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/P3394Agent.vue'), 'utf8')

    expect(source).toContain('p3394-workbench')
    expect(source).toContain('workbench-collapsed')
    expect(source).toContain('activeWorkbenchTab')
    expect(source).toContain("activeWorkbenchTab === 'artifacts'")
    expect(source).toContain("activeWorkbenchTab === 'knowledge'")
    expect(source).toContain("activeWorkbenchTab === 'execution'")
    expect(source).toContain('文件产物')
    expect(source).toContain('本地知识库')
    expect(source).toContain('执行记录')
    expect(source).toContain('knowledgeImportPath')
    expect(source).toContain('importKnowledge')
    expect(source).toContain('dropKnowledgeFiles')
    expect(source).toContain('knowledgeFileInput')
    expect(source).toContain('knowledgeFolderInput')
    expect(source).toContain('openArtifactPath')
    expect(source).toContain('readStepLabel')
    expect(source).toContain('loadWorkbench')
    expect(source).toContain('p3394Api.artifacts')
    expect(source).toContain('p3394Api.importKnowledge')
    expect(source).toContain('p3394Api.importKnowledgeFiles')
    expect(source).toContain('p3394Api.openPath')
    expect(source).toContain('p3394Api.executionSummary')
    expect(source).not.toContain('workbench-side-panel')
  })

  it('keeps optional compact-chat plumbing available for other embedding surfaces', () => {
    const chatSource = readFileSync(resolve(process.cwd(), 'src/views/AgentChat.vue'), 'utf8')
    const inputSource = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf8')

    expect(chatSource).toContain('autoApproveToolConfirmations')
    expect(chatSource).toContain('submitConfirmRequestFor(this, request, true)')
    expect(chatSource).toContain('if (vm?.compact) return normalized')
    expect(inputSource).toContain('showClearButton')
    expect(inputSource).toContain('showContextMeter')
    expect(inputSource).toContain('confirmActions && mode.confirm')
  })

  it('keeps P3394 record APIs available for future native panels', () => {
    const apiSource = readFileSync(resolve(process.cwd(), 'src/api/index.js'), 'utf8')

    expect(apiSource).toContain('export const p3394Api')
    expect(apiSource).toContain("repairApp: (id) => api.post(`/dashboard/template-library/apps/${id}/repair`)")
    expect(apiSource).toContain("taskHistory: (params) => api.get('/p3394/task-history'")
    expect(apiSource).toContain("executionRecords: (params) => api.get('/p3394/execution-records'")
    expect(apiSource).toContain("toolRecords: (params) => api.get('/p3394/tool-records'")
    expect(apiSource).toContain("fileContext: (params) => api.get('/p3394/file-context'")
    expect(apiSource).toContain("artifacts: (params) => api.get('/p3394/artifacts'")
    expect(apiSource).toContain("openPath: (data) => api.post('/p3394/open-path', data)")
    expect(apiSource).toContain("importKnowledge: (data) => api.post('/p3394/knowledge/import', data)")
    expect(apiSource).toContain("importKnowledgeFiles: (formData) => api.post('/p3394/knowledge/import-files', formData")
    expect(apiSource).toContain("executionSummary: (params) => api.get('/p3394/execution-summary'")
  })
})
