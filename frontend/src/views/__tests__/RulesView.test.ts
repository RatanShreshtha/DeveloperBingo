import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RulesView from '../RulesView.vue'
import { PRIZE_LABELS } from '../../utils/prizes'

describe('RulesView', () => {
  it('lists every prize label', () => {
    const wrapper = mount(RulesView)
    for (const label of Object.values(PRIZE_LABELS)) {
      expect(wrapper.text()).toContain(label)
    }
  })
})
