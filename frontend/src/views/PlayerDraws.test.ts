import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useLobbyStore } from '../stores/lobby'
import PlayerLobbyView from './PlayerLobbyView.vue'

vi.mock('../api/games', () => ({
  createGame: vi.fn(),
}))
vi.mock('../realtime/socket', () => ({
  joinGame: vi.fn(),
  watchLobby: vi.fn(),
  onLobbyUpdated: vi.fn(),
  startGame: vi.fn(),
  drawTopic: vi.fn(),
  onGameStarted: vi.fn(),
  onTopicDrawn: vi.fn(),
}))

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('PlayerLobbyView draws', () => {
  it('shows the draw history in order and the latest explanation', () => {
    const store = useLobbyStore()
    store.draws = [
      { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' },
      { position: 2, name: 'JSON', explanation: 'A lightweight data format.' },
    ]

    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const history = wrapper.findAll('[data-test="draw-history"] li').map((li) => li.text())
    expect(history).toHaveLength(2)
    expect(history[0]).toContain('Algorithm')
    expect(history[1]).toContain('JSON')
    expect(wrapper.text()).toContain('A lightweight data format.')
  })
})
