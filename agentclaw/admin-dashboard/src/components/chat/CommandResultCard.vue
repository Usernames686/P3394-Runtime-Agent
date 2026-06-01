<template>
  <div
    v-if="command"
    class="command-result-card mono-font"
    :class="{ failed: command.failed, running: command.running, embedded }"
    data-testid="command-result-card"
  >
    <div class="command-result-header">
      <span class="command-status-dot" :class="{ failed: command.failed, running: command.running }"></span>
      <span class="command-tool-name">{{ command.toolName }}</span>
      <span class="command-meta">{{ commandStatus }}</span>
      <span v-if="duration" class="command-meta">{{ duration }}</span>
    </div>
    <div v-if="command.cwd" class="command-cwd">cwd {{ command.cwd }}</div>
    <pre class="command-line" data-testid="command-line">{{ command.command }}</pre>
    <div v-if="command.stdout" class="command-output-section">
      <span class="command-output-label">stdout</span>
      <pre class="command-output stdout" data-testid="command-stdout">{{ command.stdout }}</pre>
    </div>
    <div v-if="command.stderr" class="command-output-section">
      <span class="command-output-label">stderr</span>
      <pre class="command-output stderr" data-testid="command-stderr">{{ command.stderr }}</pre>
    </div>
    <div v-if="!command.stdout && !command.stderr" class="command-empty">No output</div>
  </div>
</template>

<script>
import { commandStatusText, formatCommandDuration, normalizeCommandResult } from '../../utils/commandResult'

export default {
  name: 'CommandResultCard',
  props: {
    tool: { type: Object, required: true },
    embedded: { type: Boolean, default: false },
  },
  computed: {
    command() {
      return normalizeCommandResult(this.tool)
    },
    commandStatus() {
      return commandStatusText(this.command)
    },
    duration() {
      return formatCommandDuration(this.tool)
    },
  },
}
</script>

<style scoped>
.mono-font {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
}

.command-result-card {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 10px;
  border: 1px solid #dce2ea;
  border-radius: 8px;
  background: #ffffff;
  color: #20242a;
  box-shadow: 0 16px 34px -30px rgba(31, 41, 55, 0.34);
}

.command-result-card.embedded {
  width: min(100%, 760px);
  margin-top: 2px;
}

.command-result-card.failed {
  border-color: #f0c8c8;
  background: #fff8f8;
  color: #541d1d;
}

.command-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.command-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #2f8f65;
  flex: 0 0 auto;
  box-shadow: 0 0 0 4px rgba(47, 143, 101, 0.12);
}

.command-status-dot.running {
  background: #58728e;
  box-shadow: 0 0 0 4px rgba(88, 114, 142, 0.14);
}

.command-status-dot.failed {
  background: #c2413d;
  box-shadow: 0 0 0 4px rgba(194, 65, 61, 0.13);
}

.command-tool-name {
  font-weight: 760;
  color: #20242a;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-result-card.failed .command-tool-name {
  color: #8f2727;
}

.command-meta {
  color: #6f7a86;
  font-size: 12px;
  margin-left: auto;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.command-meta + .command-meta {
  margin-left: 0;
}

.command-cwd {
  color: #6f7a86;
  font-size: 12px;
  word-break: break-all;
}

.command-line {
  margin: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: #f3f6f9;
  color: #20242a;
  white-space: pre-wrap;
  word-break: break-word;
}

.command-output-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.command-output-label {
  color: #6f7a86;
  font-weight: 700;
  font-size: 11px;
  text-transform: none;
  letter-spacing: 0;
}

.command-output {
  margin: 0;
  max-height: 220px;
  overflow: auto;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #e2e7ee;
  background: #f8fafb;
  white-space: pre-wrap;
  word-break: break-word;
}

.command-output.stdout {
  color: #254f3e;
}

.command-output.stderr {
  color: #9a2d2d;
  background: #fff7f7;
  border-color: #f0c8c8;
}

.command-empty {
  color: #7b8490;
  font-size: 12px;
}
</style>
