import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PrizeBoard from '../PrizeBoard.vue'

describe('PrizeBoard', () => {
  it('shows a prize nobody holds as still open', () => {
    const wrapper = mount(PrizeBoard, {
      props: { prizes: [{ prize: 'early_five', awarded_to: [] }] },
    })

    expect(wrapper.text()).toContain('Early five: still open')
  })

  it('shows every player a prize was awarded to', () => {
    const wrapper = mount(PrizeBoard, {
      props: { prizes: [{ prize: 'early_five', awarded_to: ['Ada', 'Grace'] }] },
    })

    expect(wrapper.text()).toContain('Early five: awarded to Ada, Grace')
  })
})
