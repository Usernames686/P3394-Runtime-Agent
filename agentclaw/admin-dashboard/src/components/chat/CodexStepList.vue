<template>
  <div v-if="items.length" class="codex-step-strip" data-testid="codex-step-strip">
    <span
      v-for="item in items"
      :key="item.kind"
      class="codex-step-pill"
      :class="item.kind"
      :data-step-kind="item.kind"
    >
      <span class="codex-step-label">{{ labelFor(item.kind) }}</span>
      <span class="codex-step-detail mono-font">{{ item.detail }}</span>
      <span v-if="item.extraCount" class="codex-step-more mono-font">+{{ item.extraCount }}</span>
    </span>
  </div>
</template>

<script>
import { buildCodexStepItems } from '../../utils/codexStepSummary'

export default {
  name: 'CodexStepList',
  props: {
    step: { type: Object, default: null },
    tools: { type: Array, default: null },
    labelPrefix: { type: String, default: 'codexStep' },
  },
  computed: {
    items() {
      return buildCodexStepItems(this.tools || this.step)
    },
  },
  methods: {
    labelFor(kind) {
      const key = `${this.labelPrefix}.${kind}`
      const label = this.$t ? this.$t(key) : key
      return label === key ? {
        read: '读取',
        run: '命令',
        write: '写入',
        verify: '验证',
      }[kind] || kind : label
    },
  },
}
</script>

<style scoped>
.mono-font {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
}

.codex-step-strip {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px 10px;
  margin-top: 7px;
  padding-top: 7px;
  border-top: 1px solid rgba(226, 232, 240, 0.72);
}

.codex-step-pill {
  min-width: 0;
  max-width: 100%;
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  color: var(--text-sec, #52525b);
  font-size: 11.5px;
  line-height: 1.45;
}

.codex-step-label {
  flex: 0 0 auto;
  color: var(--text-main, #18181b);
  font-size: 11.5px;
  font-weight: 650;
}

.codex-step-detail {
  min-width: 0;
  max-width: min(34vw, 260px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-muted, #71717a);
}

.codex-step-more {
  font-size: 11px;
  color: var(--text-muted, #a1a1aa);
}

.codex-step-pill.read .codex-step-label {
  color: #1d4ed8;
}

.codex-step-pill.run .codex-step-label {
  color: #334155;
}

.codex-step-pill.write .codex-step-label {
  color: #0f766e;
}

.codex-step-pill.verify .codex-step-label {
  color: #15803d;
}
</style>
