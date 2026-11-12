import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePlayerSession } from '../../../stores/session'
import PlayerLobbyView from './PlayerPage.vue'
import { joinedAda, startFresh } from '../../../testing/testSetup'

vi.mock('../../../api/games', async () => (await import('../../../testing/apiMock')).apiGamesMock())

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

  it('disables every tick once the game has ended', async () => {
    await setUpTicket({ status: 'ended', end_reason: 'host', ticks: ['Algorithm'] })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.findAll('[data-test="tick-cell"]').every((c) => c.attributes('disabled') !== undefined)).toBe(true)
    expect(usePlayerSession().ended).toBe(true)
  })
})
