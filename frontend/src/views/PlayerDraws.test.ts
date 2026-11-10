import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useLobbyStore } from '../stores/lobby'
import PlayerLobbyView from './PlayerLobbyView.vue'

vi.mock('../api/games', () => ({
  createGame: vi.fn(),
}))
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('PlayerLobbyView draws', () => {
  it('shows every drawn topic with its explanation, in order', () => {
    const store = useLobbyStore()
    store.draws = [
      { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' },
      { position: 2, name: 'JSON', explanation: 'A lightweight data format.' },
    ]

    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const history = wrapper.findAll('[data-test="draw-history"] li').map((li) => li.text())
    expect(history).toHaveLength(2)
    expect(history[0]).toContain('Algorithm')
    expect(history[0]).toContain('A finite sequence of steps.')
    expect(history[1]).toContain('JSON')
    expect(history[1]).toContain('A lightweight data format.')
  })

  it('says the game is still waiting to start before the host starts it', () => {
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Waiting for the host to start the game.')
  })

  it('says the game has started once it has', () => {
    const store = useLobbyStore()
    store.started = true

    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('The game has started.')
  })
})
