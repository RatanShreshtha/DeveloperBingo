import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { onLobbyUpdated, watchLobby } from '../realtime/socket'
import { makePlugins } from './testRouter'
import HostView from './HostView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())
vi.mock('../api/pools', () => ({
  fetchGamePool: vi.fn(async () => ({
    name: 'Platform Team',
    columns: [
      [{ name: 'Algorithm', explanation: 'A finite sequence of steps.' }],
      [{ name: 'JSON', explanation: 'A lightweight data format.' }],
    ],
  })),
}))

beforeEach(() => {
  vi.mocked(watchLobby).mockReset()
  vi.mocked(onLobbyUpdated).mockReset()
})

describe('HostView', () => {
  it('shows the pool the game was created with as columns of topics with their explanations', async () => {
    vi.mocked(watchLobby).mockResolvedValue({ ok: true, players: [], prizes: [{ prize: 'early_five', awarded_to: [] }], claims: [] })

    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 'secret-token' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Platform Team')
    expect(wrapper.text()).toContain('Column 1')
    expect(wrapper.text()).toContain('Algorithm')
    expect(wrapper.text()).toContain('A finite sequence of steps.')
    expect(wrapper.text()).toContain('Column 2')
    expect(wrapper.text()).toContain('JSON')
  })

  it('shows the players the server reports for the lobby', async () => {
    vi.mocked(watchLobby).mockResolvedValue({ ok: true, players: ['Ada'], prizes: [{ prize: 'early_five', awarded_to: [] }], claims: [] })

    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 'secret-token' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()

    expect(watchLobby).toHaveBeenCalledWith({ code: 'ABC123', host_token: 'secret-token' })
    expect(wrapper.text()).toContain('Ada')
  })

  it('updates the list when a lobby update arrives', async () => {
    vi.mocked(watchLobby).mockResolvedValue({ ok: true, players: ['Ada'], prizes: [{ prize: 'early_five', awarded_to: [] }], claims: [] })
    let notify: (players: string[]) => void = () => {}
    vi.mocked(onLobbyUpdated).mockImplementation((handler) => {
      notify = handler
    })

    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 'secret-token' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()
    notify(['Ada', 'Grace'])
    await flushPromises()

    expect(wrapper.text()).toContain('Grace')
  })

  it('explains when the host link is not valid for the game', async () => {
    vi.mocked(watchLobby).mockResolvedValue({ ok: false, error: 'not_host' })

    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 'wrong-token' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('This host link is not valid for this game')
  })
})
