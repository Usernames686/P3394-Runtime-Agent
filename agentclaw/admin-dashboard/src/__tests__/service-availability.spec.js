import { describe, expect, it } from 'vitest'
import { isFeatureAvailableFromHealth } from '../composables/useServiceAvailability'

describe('service availability gates', () => {
  it('treats explicit unavailable admin features as unavailable', () => {
    const health = {
      features: {
        knowledgebases: { available: false },
        scheduler: false,
        channels: { available: true },
      },
    }

    expect(isFeatureAvailableFromHealth(health, 'knowledgebases')).toBe(false)
    expect(isFeatureAvailableFromHealth(health, 'scheduler')).toBe(false)
    expect(isFeatureAvailableFromHealth(health, 'channels')).toBe(true)
  })

  it('keeps old health payloads compatible when no feature map is present', () => {
    expect(isFeatureAvailableFromHealth({ status: 'ok', service: 'admin' }, 'scheduler')).toBe(true)
  })

  it('can fail closed for optional admin pages while health is unavailable', () => {
    expect(isFeatureAvailableFromHealth(null, 'scheduler', { fallback: false })).toBe(false)
    expect(isFeatureAvailableFromHealth({ status: 'ok', service: 'admin' }, 'scheduler', { fallback: false })).toBe(false)
  })
})
