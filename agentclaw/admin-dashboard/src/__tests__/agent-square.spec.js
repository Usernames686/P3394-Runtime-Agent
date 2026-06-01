import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Template Library workflow separation', () => {
  it('adds a Template Library route and keeps Agent Square out of the UI', () => {
    const routerSource = readFileSync(resolve(process.cwd(), 'src/router/index.js'), 'utf8')
    const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/Sidebar.vue'), 'utf8')

    expect(routerSource).toContain("path: '/templates'")
    expect(routerSource).toContain("name: 'TemplateLibrary'")
    expect(routerSource).toContain("TemplateLibrary.vue")
    expect(sidebarSource).toContain("t('nav.templates')")
    expect(sidebarSource).toContain("key: '/templates'")
    expect(sidebarSource).toContain("path.startsWith('/templates')")
    expect(routerSource).not.toContain("path: '/agent-square'")
    expect(routerSource).not.toContain("name: 'AgentSquare'")
    expect(routerSource).not.toContain("AgentSquare.vue")
    expect(sidebarSource).not.toContain("t('nav.agentSquare')")
    expect(sidebarSource).not.toContain("key: '/agent-square'")
    expect(sidebarSource).not.toContain("path.startsWith('/agent-square')")
  })

  it('packages the admin shell as a P3394-first platform', () => {
    const routerSource = readFileSync(resolve(process.cwd(), 'src/router/index.js'), 'utf8')
    const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/Sidebar.vue'), 'utf8')
    const htmlSource = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')

    expect(routerSource).toContain("redirect: '/p3394-agent'")
    expect(sidebarSource).toContain("brand.shortName")
    expect(htmlSource).toContain('<title>P3394 Agent Platform</title>')
  })

  it('places the P3394 Agent entry before the base agent and Template Library', () => {
    const routerSource = readFileSync(resolve(process.cwd(), 'src/router/index.js'), 'utf8')
    const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/Sidebar.vue'), 'utf8')
    const zhSource = readFileSync(resolve(process.cwd(), 'src/locales/zh-CN.js'), 'utf8')
    const enSource = readFileSync(resolve(process.cwd(), 'src/locales/en-US.js'), 'utf8')

    expect(routerSource).toContain("path: '/p3394-agent'")
    expect(routerSource).toContain("name: 'P3394Agent'")
    expect(routerSource).toContain("P3394Agent.vue")
    expect(sidebarSource).toContain("t('nav.p3394Agent')")
    expect(sidebarSource).toContain("key: '/p3394-agent'")
    expect(sidebarSource).toContain("path.startsWith('/p3394-agent')")
    expect(zhSource).toContain("p3394Agent: 'P3394 主智能体'")
    expect(enSource).toContain("p3394Agent: 'P3394 Agent'")

    const p3394Index = sidebarSource.indexOf("key: '/p3394-agent'")
    const builtinIndex = sidebarSource.indexOf("key: '/builtin'")
    const templatesIndex = sidebarSource.indexOf("key: '/templates'")

    expect(p3394Index).toBeGreaterThanOrEqual(0)
    expect(builtinIndex).toBeGreaterThan(p3394Index)
    expect(templatesIndex).toBeGreaterThan(builtinIndex)
  })

  it('keeps the main sidebar focused on P3394, base agent, templates, and settings', () => {
    const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/Sidebar.vue'), 'utf8')

    expect(sidebarSource).toContain("key: '/builtin'")
    expect(sidebarSource).toContain("key: '/p3394-agent'")
    expect(sidebarSource).toContain("key: '/templates'")
    expect(sidebarSource).toContain("router.push('/settings')")
    expect(sidebarSource).not.toContain("key: '/workflows'")
    expect(sidebarSource).not.toContain("key: '/knowledgebases'")
    expect(sidebarSource).not.toContain("key: '/scheduler'")
    expect(sidebarSource).not.toContain("key: '/channels'")
    expect(sidebarSource).not.toContain("key: '/dashboard'")
  })

  it('keeps unimported templates out of the workflow list', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/Workflows.vue'), 'utf8')

    expect(source).not.toContain('agentFilter')
    expect(source).not.toContain("value: 'agent_square'")
    expect(source).not.toContain('workflows.filterAgentSquare')
    expect(source).not.toContain("workflowsApi.list({ include_builtin: true })")
    expect(source).toContain("workflowsApi.list({ include_builtin: false })")
    expect(source).not.toContain('wf.agent_square_app_id')
  })

  it('imports templates and opens imported agents with the recommended input', () => {
    const templateSource = readFileSync(resolve(process.cwd(), 'src/views/TemplateLibrary.vue'), 'utf8')
    const chatSource = readFileSync(resolve(process.cwd(), 'src/views/AgentChat.vue'), 'utf8')

    expect(templateSource).toContain('templateLibraryApi.list')
    expect(templateSource).toContain('templateLibraryApi.importApp')
    expect(templateSource).toContain('openWorkflow(app)')
    expect(templateSource).toContain('seed_input')
    expect(templateSource).toContain('app.recommended_input')
    expect(templateSource).toContain('v-if="!app.registered"')
    expect(templateSource).not.toContain(':disabled="app.imported && !app.registered"')
    expect(chatSource).toContain('function getRouteSeedInput')
    expect(chatSource).toContain('} else if (seedInput) {')
    expect(chatSource).toContain('seedInput && !this.inputText && this.userInputFieldName')
    expect(chatSource).toContain('this.inputText = seedInput')
  })

  it('keeps the P3394 entry as the native AgentClaw chat page', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/views/P3394Agent.vue'), 'utf8')
    const chatSource = readFileSync(resolve(process.cwd(), 'src/views/AgentChat.vue'), 'utf8')

    expect(source).toContain('p3394-agent-page')
    expect(source).toContain("'is-ready': registered")
    expect(source).toContain('<AgentChat')
    expect(source).toContain(':workflow-id="workflowId"')
    expect(source).toContain('p3394-workbench')
    expect(source).toContain('workbench-collapsed')
    expect(source).toContain('activeWorkbenchTab')
    expect(source).toContain('文件产物')
    expect(source).toContain('本地知识库')
    expect(source).toContain('执行记录')
    expect(chatSource).toContain("v-if=\"!compact\"")
    expect(chatSource).toContain("v-if=\"!isPublicMode && !compact\"")
    expect(chatSource).toContain('if (this.hideConfigPanel) return []')
    expect(chatSource).toContain('if (this.hideProcessDetails) return false')
    expect(chatSource).toContain('} else if (this.compact) {')
    expect(source).toContain('你的默认主智能体，基于 AgentClaw 运行时')
    expect(source).toContain('启用 P3394 主智能体')
    expect(source).not.toContain('compact hide-config-panel hide-process-details')
    expect(source).not.toContain('<PageHeader')
    expect(source).not.toContain('打开独立聊天')
    expect(source).not.toContain('task-strip')
    expect(source).not.toContain('detail-toggle')
    expect(source).not.toContain('runtime-detail-panel')
    expect(source).not.toContain('routeMap')
    expect(source).not.toContain('quickPrompts')
    expect(source).not.toContain('orchestrationTimeline')
    expect(source).not.toContain('orchestration-rail')
    expect(source).not.toContain('quick-tile')
    expect(source).not.toContain('route-list')
    expect(source).not.toContain('Manifest / UMF / Session / Capability Router / Audit')
    expect(source).not.toContain('先接收自然语言或 UMF 消息')
    expect(source).not.toContain('openChat')
  })
})
