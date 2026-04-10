import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AdvancedSettings from '../AdvancedSettings.vue'

const TooltipIcon = { template: '<span />', props: ['text'] }

describe('AdvancedSettings', () => {
  function createWrapper(overrides = {}) {
    return mount(AdvancedSettings, {
      props: {
        modelValue: {
          jobName: '',
          email: '',
          interfaceCutoff: 5.0,
          waterCutoff: 5.0,
          useReduce: false,
          frameStep: 1,
          useCustomInterval: false,
          startFrame: 1,
          endFrame: 50,
          ...overrides,
        },
        totalFrames: 100,
        maxFrames: 50,
      },
      global: {
        stubs: { TooltipIcon },
      },
    })
  }

  async function expandSettings(wrapper) {
    const toggleBtn = wrapper.find('.settings-toggle')
    await toggleBtn.trigger('click')
  }

  it('renders the reduce toggle when expanded', async () => {
    const wrapper = createWrapper()
    await expandSettings(wrapper)
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes.length).toBeGreaterThan(0)
  })

  it('defaults useReduce to OFF', async () => {
    const wrapper = createWrapper()
    await expandSettings(wrapper)
    expect(wrapper.text()).toContain('OFF')
  })

  it('emits useReduce=true when toggled on', async () => {
    const wrapper = createWrapper({ useReduce: false })
    await expandSettings(wrapper)

    // The reduce toggle is the first checkbox in the expanded panel
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    const reduceCheckbox = checkboxes[0]
    await reduceCheckbox.setValue(true)

    const emitted = wrapper.emitted('update:settings')
    expect(emitted).toBeTruthy()
    const lastEmission = emitted[emitted.length - 1][0]
    expect(lastEmission.useReduce).toBe(true)
  })

  it('shows ON when useReduce is true', async () => {
    const wrapper = createWrapper({ useReduce: true })
    await expandSettings(wrapper)
    expect(wrapper.text()).toContain('ON')
  })
})
