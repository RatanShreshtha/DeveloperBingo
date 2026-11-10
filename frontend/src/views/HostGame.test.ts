import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { drawTopic, startGame, watchLobby } from '../realtime/socket'
import { makePlugins } from './testRouter'
import HostView from './HostView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../api/pools', () => ({
  fetchDefaultPool: vi.fn(async () => ({ columns: [] })),
}))
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  vi.mocked(watchLobby).mockResolvedValue({ ok: true, players: ['Ada'], prizes: { early_five: null } })
  vi.mocked(startGame).mockReset()
  vi.mocked(drawTopic).mockReset()
})

function mountHost() {
  return mount(HostView, {
    props: { code: 'ABC123', token: 'secret-token' },
    global: { plugins: makePlugins() },
  })
}

async function startTheGame(wrapper: ReturnType<typeof mountHost>) {
  vi.mocked(startGame).mockResolvedValue({ ok: true })
  await wrapper.get('[data-test="start-game"]').trigger('click')
  await flushPromises()
}

describe('HostView game flow', () => {
  it('starts the game when the host presses Start', async () => {
    const wrapper = mountHost()
    await flushPromises()

    await startTheGame(wrapper)

    expect(startGame).toHaveBeenCalledWith({ code: 'ABC123', token: 'secret-token' })
    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(true)
  })

  it('shows the drawn topic and its explanation after a draw', async () => {
    vi.mocked(drawTopic).mockResolvedValue({
      ok: true,
      draw: { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' },
    })
    const wrapper = mountHost()
    await flushPromises()
    await startTheGame(wrapper)

    await wrapper.get('[data-test="draw-topic"]').trigger('click')
    await flushPromises()

    expect(drawTopic).toHaveBeenCalledWith({ code: 'ABC123', token: 'secret-token' })
    expect(wrapper.text()).toContain('Algorithm')
    expect(wrapper.text()).toContain('A finite sequence of steps.')
  })

  it('keeps the Draw control and explains a refused draw', async () => {
    vi.mocked(drawTopic).mockResolvedValue({ ok: false, error: 'no_topics_left' })
    const wrapper = mountHost()
    await flushPromises()
    await startTheGame(wrapper)

    await wrapper.get('[data-test="draw-topic"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Every topic has already been drawn')
  })

  it('shows no game controls when the host link is refused', async () => {
    vi.mocked(watchLobby).mockResolvedValue({ ok: false, error: 'not_host' })
    const wrapper = mountHost()
    await flushPromises()

    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('This host link is not valid for this game')
  })
})
