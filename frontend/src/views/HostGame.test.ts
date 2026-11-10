import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { drawTopic, startGame, watchLobby } from '../realtime/socket'
import { makePlugins } from './testRouter'
import HostView from './HostView.vue'

vi.mock('../api/games', () => ({
  createGame: vi.fn(),
}))
vi.mock('../api/pools', () => ({
  fetchDefaultPool: vi.fn(async () => ({ columns: [] })),
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
  vi.mocked(watchLobby).mockResolvedValue({ ok: true, players: ['Ada'] })
  vi.mocked(startGame).mockReset()
  vi.mocked(drawTopic).mockReset()
})

function mountHost() {
  return mount(HostView, {
    props: { code: 'ABC123', token: 'secret-token' },
    global: { plugins: makePlugins() },
  })
}

describe('HostView game flow', () => {
  it('starts the game when the host presses Start', async () => {
    vi.mocked(startGame).mockResolvedValue({ ok: true })
    const wrapper = mountHost()
    await flushPromises()

    await wrapper.get('[data-test="start-game"]').trigger('click')
    await flushPromises()

    expect(startGame).toHaveBeenCalledWith('ABC123', 'secret-token')
    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(true)
  })

  it('shows the drawn topic and its explanation after a draw', async () => {
    vi.mocked(startGame).mockResolvedValue({ ok: true })
    vi.mocked(drawTopic).mockResolvedValue({
      ok: true,
      draw: { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' },
    })
    const wrapper = mountHost()
    await flushPromises()
    await wrapper.get('[data-test="start-game"]').trigger('click')
    await flushPromises()

    await wrapper.get('[data-test="draw-topic"]').trigger('click')
    await flushPromises()

    expect(drawTopic).toHaveBeenCalledWith('ABC123', 'secret-token')
    expect(wrapper.text()).toContain('Algorithm')
    expect(wrapper.text()).toContain('A finite sequence of steps.')
  })
})
