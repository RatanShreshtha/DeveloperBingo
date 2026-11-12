import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TicketGrid from '../TicketGrid.vue'

const ticket = [
  ['Algorithm', null, 'JSON'],
  [null, 'Cache', null],
]

function render(props: Partial<InstanceType<typeof TicketGrid>['$props']> = {}) {
  return mount(TicketGrid, { props: { ticket, ticks: [], drawn: ['Algorithm'], ended: false, ...props } })
}

describe('TicketGrid', () => {
  it('emits the topic when a drawn cell is clicked', async () => {
    const wrapper = render()

    await wrapper.findAll('[data-test="tick-cell"]')[0].trigger('click')

    expect(wrapper.emitted('toggle')).toEqual([['Algorithm']])
  })

  it('disables topics that have not been drawn yet', () => {
    const cells = render().findAll('[data-test="tick-cell"]')

    expect(cells.find((cell) => cell.text() === 'Cache')?.attributes('disabled')).toBeDefined()
    expect(cells[0].attributes('disabled')).toBeUndefined()
  })

  it('shows ticked topics as pressed', () => {
    const wrapper = render({ ticks: ['Algorithm'] })

    expect(wrapper.findAll('[data-test="tick-cell"]')[0].attributes('aria-pressed')).toBe('true')
  })

  it('disables every cell once the game has ended', () => {
    const wrapper = render({ ended: true, ticks: ['Algorithm'] })

    expect(wrapper.findAll('[data-test="tick-cell"]').every((c) => c.attributes('disabled') !== undefined)).toBe(true)
  })

  it('keeps the ticket in a keyboard-focusable scroll region', () => {
    expect(render().find('[role="region"]').attributes('tabindex')).toBe('0')
  })
})
