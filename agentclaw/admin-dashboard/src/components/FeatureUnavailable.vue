<template>
  <section class="feature-unavailable">
    <div class="feature-unavailable__eyebrow">{{ eyebrow }}</div>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <p v-if="reason" class="feature-unavailable__reason">{{ reason }}</p>
    <n-button secondary size="small" @click="$router.push('/builtin')">
      {{ actionLabel }}
    </n-button>
  </section>
</template>

<script setup>
import { NButton } from 'naive-ui'

defineProps({
  eyebrow: { type: String, default: 'SERVICE OFFLINE' },
  title: { type: String, required: true },
  description: { type: String, required: true },
  reason: { type: String, default: '' },
  actionLabel: { type: String, default: '返回 AgentClaw' },
})
</script>

<style scoped>
.feature-unavailable {
  min-height: 360px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: 10px;
  padding: 48px 8px;
  color: var(--text-primary);
}

.feature-unavailable__eyebrow {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0;
}

.feature-unavailable h2 {
  margin: 0;
  font-size: 22px;
  line-height: 1.3;
}

.feature-unavailable p {
  max-width: 560px;
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.feature-unavailable__reason {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px !important;
  color: #667085 !important;
}
</style>
