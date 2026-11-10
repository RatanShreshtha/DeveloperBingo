import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { claimPrize } from '../realtime/socket'
import { useLobbyStore } from '../stores/lobby'
import PlayerLobbyView from './PlayerLobbyView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(claimPrize).mockReset()
})

function setUpPlayer() {
  const store = useLobbyStore()
  store.player = { code: 'ABC123', name: 'Ada' }
  store.ticket = [['Algorithm', null, 'JSON']]
  store.started = true
  return store
}

describe('PlayerLobbyView prizes', () => {
  it('lets the player claim early five', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: true })
    setUpPlayer()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    await wrapper.get('[data-test="claim-early-five"]').trigger('click')
    await flushPromises()

    expect(claimPrize).toHaveBeenCalledWith({ code: 'ABC123', name: 'Ada' }, 'early_five')
  })

  it('shows early five as still open until someone is awarded it', () => {
    setUpPlayer()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Early five: still open')
  })

  it('hides the claim button until the game starts', () => {
    const store = setUpPlayer()
    store.started = false
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.find('[data-test="claim-early-five"]').exists()).toBe(false)
  })

  it('shows who early five was awarded to', () => {
    const store = setUpPlayer()
    store.prizes = { early_five: 'Grace' }
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Early five: awarded to Grace')
  })
})
