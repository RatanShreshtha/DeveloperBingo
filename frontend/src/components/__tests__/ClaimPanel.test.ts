import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ClaimPanel from '../ClaimPanel.vue'

const prizes = [
  { prize: 'early_five' as const, awarded_to: [] },
  { prize: 'top_line' as const, awarded_to: ['Bo'] },
]

describe('ClaimPanel', () => {
  it('emits the prize when its claim button is clicked', async () => {
    const wrapper = mount(ClaimPanel, { props: { prizes, pending: [] } })

    await wrapper.get('[data-test="claim-early_five"]').trigger('click')

    expect(wrapper.emitted('claim')).toEqual([['early_five']])
  })

  it('disables a prize that is awarded', () => {
    const wrapper = mount(ClaimPanel, { props: { prizes, pending: [] } })

    expect(
      wrapper.get('[data-test="claim-top_line"]').attributes('disabled'),
    ).toBeDefined()
  })

  it('shows a pending claim as claiming and disabled', () => {
    const wrapper = mount(ClaimPanel, {
      props: { prizes, pending: ['early_five'] },
    })
    const button = wrapper.get('[data-test="claim-early_five"]')

    expect(button.text()).toBe('Claiming Early five…')
    expect(button.attributes('disabled')).toBeDefined()
  })
})
