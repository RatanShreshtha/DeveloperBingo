import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createGame } from '../api/games'
import { makePlugins } from './testRouter'
import HomeView from './HomeView.vue'

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
  vi.mocked(createGame).mockReset()
})

describe('HomeView', () => {
  it('creates a game and shows the code and the private host link', async () => {
    vi.mocked(createGame).mockResolvedValue({ code: 'ABC123', host_token: 'secret-token' })
    const wrapper = mount(HomeView, { global: { plugins: makePlugins() } })

    await wrapper.get('button[data-test="create-game"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('ABC123')
    expect(wrapper.text()).toContain('/host/ABC123?token=secret-token')
  })
})
