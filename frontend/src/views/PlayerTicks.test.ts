import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { tickTopic } from '../realtime/socket'
import { useLobbyStore } from '../stores/lobby'
import PlayerLobbyView from './PlayerLobbyView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(tickTopic).mockReset()
})

function setUpTicket() {
  const store = useLobbyStore()
  store.playerCode = 'ABC123'
  store.playerName = 'Ada'
  store.ticket = [
    ['Algorithm', null, 'JSON'],
    [null, 'Cache', null],
  ]
  store.draws = [{ position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' }]
  return store
}

describe('PlayerLobbyView ticking', () => {
  it('lets the player tick a drawn topic on their ticket', async () => {
    vi.mocked(tickTopic).mockResolvedValue({ ok: true, ticked: ['Algorithm'] })
    const store = setUpTicket()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    await wrapper.findAll('[data-test="tick-cell"]')[0].trigger('click')
    await flushPromises()

    expect(tickTopic).toHaveBeenCalledWith('ABC123', 'Ada', 'Algorithm')
    expect(store.ticked).toEqual(['Algorithm'])
  })

  it('disables topics that have not been drawn yet', () => {
    setUpTicket()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const cells = wrapper.findAll('[data-test="tick-cell"]')
    const cacheCell = cells.find((cell) => cell.text() === 'Cache')
    expect(cacheCell?.attributes('disabled')).toBeDefined()
    expect(wrapper.findAll('[data-test="tick-cell"]')[0].attributes('disabled')).toBeUndefined()
  })

  it('shows ticked topics as pressed on the ticket', async () => {
    const store = setUpTicket()
    store.ticked = ['Algorithm']
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const algorithm = wrapper.findAll('[data-test="tick-cell"]')[0]
    expect(algorithm.attributes('aria-pressed')).toBe('true')
  })
})
