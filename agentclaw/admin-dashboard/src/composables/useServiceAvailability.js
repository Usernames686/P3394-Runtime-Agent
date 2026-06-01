import { computed, onMounted, ref } from 'vue'
import { adminApi } from '../api'

const health = ref(null)
const loading = ref(false)
const error = ref(null)
let pending = null

export function isFeatureAvailableFromHealth(payload, featureName, { fallback = true } = {}) {
  const features = payload?.features
  if (!features || !(featureName in features)) return fallback

  const feature = features[featureName]
  if (typeof feature === 'boolean') return feature
  return feature?.available !== false
}

export function featureReasonFromHealth(payload, featureName) {
  const feature = payload?.features?.[featureName]
  if (feature && typeof feature === 'object') return feature.reason || ''
  return ''
}

export async function refreshServiceAvailability() {
  if (pending) return pending
  loading.value = true
  pending = adminApi.health()
    .then((payload) => {
      health.value = payload
      error.value = null
      return payload
    })
    .catch((err) => {
      error.value = err
      return null
    })
    .finally(() => {
      loading.value = false
      pending = null
    })
  return pending
}

export function useServiceAvailability({ autoLoad = true } = {}) {
  if (autoLoad) onMounted(refreshServiceAvailability)

  return {
    health,
    loading,
    error,
    refresh: refreshServiceAvailability,
    isAvailable: (featureName, options) => isFeatureAvailableFromHealth(health.value, featureName, options),
    reason: (featureName) => featureReasonFromHealth(health.value, featureName),
    featureMap: computed(() => health.value?.features || {}),
  }
}
