import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import ChatMessage from '../components/chat/ChatMessage.vue'
import StreamingMessage from '../components/chat/StreamingMessage.vue'

describe('ChatMessage command tool display', () => {
  it('shows a command result card by default for compact command tool calls', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        processCollapsed: false,
        msg: {
          role: 'assistant',
          content: 'done',
          timestamp: Date.now(),
          toolCalls: [{
            id: 'call-shell',
            name: 'shell',
            arguments: JSON.stringify({ command: 'pwd' }),
            result: 'D:\\codex\\ui\\agentclaw',
            status: 'completed',
            elapsed: '36ms',
          }],
        },
      },
      global: {
        mocks: {
          $i18n: { locale: 'zh-CN' },
          $t: (key) => key,
        },
      },
    })

    expect(wrapper.find('[data-testid="command-result-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="command-line"]').text()).toBe('pwd')
    expect(wrapper.find('[data-testid="command-stdout"]').text()).toContain('D:\\codex\\ui\\agentclaw')
  })

  it('renders Codex-like process step summaries for saved assistant messages', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        processCollapsed: false,
        msg: {
          role: 'assistant',
          content: 'done',
          timestamp: Date.now(),
          nodeSteps: [{
            id: 'agent',
            name: 'P3394 Runtime Agent',
            status: 'succeeded',
            expanded: true,
            inputs: { file: 'src/views/P3394Agent.vue' },
            outputs: { artifact_path: 'docs/P3394-Runtime-Agent.md', result: '16 passed' },
            toolCalls: [{
              id: 'call-shell',
              name: 'shell',
              arguments: JSON.stringify({ command: 'npm test -- src/__tests__/memory-graph.spec.js' }),
              result: { stdout: '16 passed', exit_code: 0 },
              status: 'completed',
            }],
          }],
        },
      },
      global: {
        mocks: {
          $i18n: { locale: 'zh-CN' },
          $t: (key) => key,
        },
      },
    })

    const summary = wrapper.find('[data-testid="codex-step-strip"]')
    expect(summary.exists()).toBe(true)
    expect(wrapper.find('[data-step-kind="read"]').text()).toContain('src/views/P3394Agent.vue')
    expect(wrapper.find('[data-step-kind="run"]').text()).toContain('npm test')
    expect(wrapper.find('[data-step-kind="write"]').text()).toContain('docs/P3394-Runtime-Agent.md')
    expect(wrapper.find('[data-step-kind="verify"]').text()).toContain('16 passed')
  })

  it('renders Codex-like process step summaries while streaming', () => {
    const wrapper = mount(StreamingMessage, {
      props: {
        processCollapsed: false,
        nodeSteps: [{
          id: 'agent',
          name: 'P3394 Runtime Agent',
          status: 'running',
          expanded: true,
          inputs: { path: 'P3394-v0.9.0-combined(2).md' },
          outputs: { file_path: 'local-demo/agents/p3394_runtime_agent/agents/agent.py' },
          toolCalls: [{
            id: 'call-shell',
            name: 'shell',
            arguments: JSON.stringify({ command: 'pytest agentclaw/test/api/test_admin_p3394_api.py -q' }),
            result: '16 passed',
            status: 'completed',
          }],
        }],
      },
      global: {
        mocks: {
          $i18n: { locale: 'zh-CN' },
          $t: (key) => key,
        },
      },
    })

    expect(wrapper.find('[data-testid="codex-step-strip"]').exists()).toBe(true)
    expect(wrapper.find('[data-step-kind="read"]').text()).toContain('P3394-v0.9.0-combined(2).md')
    expect(wrapper.find('[data-step-kind="run"]').text()).toContain('pytest')
    expect(wrapper.find('[data-step-kind="write"]').text()).toContain('local-demo/agents/p3394_runtime_agent/agents/agent.py')
    expect(wrapper.find('[data-step-kind="verify"]').text()).toContain('16 passed')
  })
})
