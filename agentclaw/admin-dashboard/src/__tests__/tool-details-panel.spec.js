import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import ToolDetailsPanel from '../components/chat/ToolDetailsPanel.vue'

describe('ToolDetailsPanel command results', () => {
  it('renders shell tool output as a command result card', () => {
    const wrapper = mount(ToolDetailsPanel, {
      props: {
        visible: true,
        tool: {
          id: 'call-shell',
          name: 'shell',
          arguments: JSON.stringify({
            command: 'pwd',
            cwd: 'D:\\codex\\ui\\agentclaw',
          }),
          result: JSON.stringify({
            stdout: 'D:\\codex\\ui\\agentclaw\n',
            stderr: '',
            exit_code: 0,
          }),
          status: 'succeeded',
          elapsed: '42ms',
        },
      },
    })

    expect(wrapper.find('[data-testid="command-result-card"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('pwd')
    expect(wrapper.text()).toContain('Exit 0')
    expect(wrapper.find('[data-testid="command-stdout"]').text()).toContain('D:\\codex\\ui\\agentclaw')
    expect(wrapper.find('[data-testid="command-stderr"]').exists()).toBe(false)
  })

  it('extracts stdout and exit code from AgentClaw shell result text', () => {
    const wrapper = mount(ToolDetailsPanel, {
      props: {
        visible: true,
        tool: {
          id: 'call-shell-failed',
          name: 'shell',
          arguments: JSON.stringify({ command: 'missing-command' }),
          result: '[ERROR] Shell command failed (exit code 9009)\n[stdout]\npartial output\n[stderr]\nnot recognized',
          status: 'failed',
        },
      },
    })

    expect(wrapper.text()).toContain('Exit 9009')
    expect(wrapper.find('[data-testid="command-stdout"]').text()).toContain('partial output')
    expect(wrapper.find('[data-testid="command-stderr"]').text()).toContain('not recognized')
  })
})
