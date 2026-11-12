import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { endGame, watchLobby } from '../realtime/socket'
import { useLobbyStore } from '../stores/lobby'
import HostView from './HostView.vue'
import PlayerLobbyView from './PlayerLobbyView.vue'
import { makePlugins } from './testRouter'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../api/pools', () => ({
  fetchDefaultPool: vi.fn(async () => ({ columns: [] })),
}))
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(watchLobby).mockResolvedValue({
    ok: true,
    players: ['Ada'],
    prizes: [{ prize: 'early_five', awarded_to: [] }],
  })
  vi.mocked(endGame).mockReset()
})

function mountHost() {
  return mount(HostView, {
    props: { code: 'ABC123', token: 'secret-token' },
    global: { plugins: makePlugins() },
  })
}

describe('HostView ending the game', () => {
  it('ends the game when the host presses End game', async () => {
    vi.mocked(endGame).mockResolvedValue({ ok: true })
    const wrapper = mountHost()
    await flushPromises()

    await wrapper.get('[data-test="end-game"]').trigger('click')
    await flushPromises()

    expect(endGame).toHaveBeenCalledWith({ code: 'ABC123', host_token: 'secret-token' })
  })

  it('takes away the start, draw and end controls once the game has ended', async () => {
    const wrapper = mountHost()
    await flushPromises()
    const store = useLobbyStore()
    store.started = true
    store.endReason = 'host'
    await flushPromises()

    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="end-game"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('You ended the game')
  })
})

describe('PlayerLobbyView when the game ends', () => {
  function setUpPlayer() {
    const store = useLobbyStore()
    store.player = { code: 'ABC123', name: 'Ada' }
    store.ticket = [['Algorithm', null, 'JSON']]
    store.started = true
    store.prizes = [{ prize: 'early_five', awarded_to: [] }]
    return store
  }

  it('tells the player the full house was claimed and removes the claim buttons', async () => {
    const store = setUpPlayer()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })
    store.endReason = 'full_house'
    await flushPromises()

    expect(wrapper.text()).toContain('The game is over: the full house was claimed')
    expect(wrapper.find('[data-test="claim-early_five"]').exists()).toBe(false)
  })

  it('tells the player the host ended the game', async () => {
    const store = setUpPlayer()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })
    store.endReason = 'host'
    await flushPromises()

    expect(wrapper.text()).toContain('The host ended the game')
  })

  it('still shows the prizes that were awarded', async () => {
    const store = setUpPlayer()
    store.prizes = [{ prize: 'early_five', awarded_to: ['Grace'] }]
    store.endReason = 'host'
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Early five: awarded to Grace')
  })
})
