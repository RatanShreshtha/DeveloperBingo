import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSessionStore } from '../stores/session'
import PlayerLobbyView from './PlayerLobbyView.vue'
import { joinedAda, startFresh } from './testSetup'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

function setUpTicket(overrides = {}) {
  return joinedAda(fake, {
    status: 'started',
    ticket: [
      ['Algorithm', null, 'JSON'],
      [null, 'Cache', null],
    ],
    draws: [{ position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' }],
    ...overrides,
  })
}

describe('PlayerLobbyView ticking', () => {
  it('lets the player tick a drawn topic on their ticket', async () => {
    fake.answer('tick_topic', { ok: true })
    const store = await setUpTicket()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    await wrapper.findAll('[data-test="tick-cell"]')[0].trigger('click')
    await flushPromises()

    expect(fake.payloads('tick_topic')).toEqual([{ topic: 'Algorithm' }])
    expect(store.ticks).toEqual(['Algorithm'])
  })

  it('disables topics that have not been drawn yet', async () => {
    await setUpTicket()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const cells = wrapper.findAll('[data-test="tick-cell"]')
    const cacheCell = cells.find((cell) => cell.text() === 'Cache')
    expect(cacheCell?.attributes('disabled')).toBeDefined()
    expect(cells[0].attributes('disabled')).toBeUndefined()
  })

  it('shows ticked topics as pressed on the ticket', async () => {
    await setUpTicket({ ticks: ['Algorithm'] })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.findAll('[data-test="tick-cell"]')[0].attributes('aria-pressed')).toBe('true')
  })

  it('disables every tick once the game has ended', async () => {
    await setUpTicket({ status: 'ended', end_reason: 'host', ticks: ['Algorithm'] })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.findAll('[data-test="tick-cell"]').every((c) => c.attributes('disabled') !== undefined)).toBe(true)
    expect(useSessionStore().ended).toBe(true)
  })
})
