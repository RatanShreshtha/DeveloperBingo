import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useLobbyStore } from '../stores/lobby'
import PlayerLobbyView from './PlayerLobbyView.vue'

vi.mock('../api/games', () => ({
  createGame: vi.fn(),
  startGame: vi.fn(),
}))
vi.mock('../realtime/socket', () => ({
  joinGame: vi.fn(),
  watchLobby: vi.fn(),
  onLobbyUpdated: vi.fn(),
}))

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('PlayerLobbyView', () => {
  it('shows the player their own ticket, with empty cells left blank', () => {
    const store = useLobbyStore()
    store.ticket = [
      ['Algorithm', null, 'JSON'],
      [null, 'Cache', null],
    ]

    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const cells = wrapper.findAll('[data-test="ticket-cell"]')
    expect(cells).toHaveLength(6)
    expect(wrapper.text()).toContain('Algorithm')
    expect(wrapper.text()).toContain('Cache')
    expect(wrapper.findAll('[data-test="ticket-cell"]').filter((c) => c.text() === '')).toHaveLength(3)
  })
})
