import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchGameHistory } from '../api/games'
import { createPinia, setActivePinia } from 'pinia'
import { watchLobby } from '../realtime/socket'
import { useLobbyStore } from '../stores/lobby'
import GameHistoryView from './GameHistoryView.vue'
import HostView from './HostView.vue'
import PlayerLobbyView from './PlayerLobbyView.vue'
import { makePlugins } from './testRouter'

vi.mock('../api/games', async () => {
  const mock = (await import('../testing/apiMock')).apiGamesMock()
  class GameHistoryError extends Error {
    status: number
    constructor(status: number) {
      super(`status ${status}`)
      this.status = status
    }
  }
  return { ...mock, GameHistoryError }
})
vi.mock('../api/pools', () => ({ fetchDefaultPool: vi.fn(async () => ({ columns: [] })) }))
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const history = {
  code: 'ABC123',
  reason: 'full_house' as const,
  pool_name: 'Default',
  draws: [
    { position: 1, name: 'Cache', explanation: 'Keeps results close' },
    { position: 2, name: 'Index', explanation: 'Speeds lookups' },
  ],
  claims: [
    { player: 'Grace', prize: 'early_five' as const, accepted: false, error: 'claim_not_valid' as const },
    { player: 'Ada', prize: 'full_house' as const, accepted: true, error: null },
  ],
  winners: [
    { prize: 'early_five' as const, awarded_to: [] },
    { prize: 'full_house' as const, awarded_to: ['Ada'] },
  ],
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(fetchGameHistory).mockReset()
})

function mountHistory() {
  return mount(GameHistoryView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
}

describe('GameHistoryView', () => {
  it('shows the draws in order with their explanations', async () => {
    vi.mocked(fetchGameHistory).mockResolvedValue(history)
    const wrapper = mountHistory()
    await flushPromises()

    const draws = wrapper.findAll('[data-test="draw"]').map((d) => d.text())
    expect(draws).toEqual(['1. Cache: Keeps results close', '2. Index: Speeds lookups'])
  })

  it('shows each claim with its outcome and the reason a refusal was made', async () => {
    vi.mocked(fetchGameHistory).mockResolvedValue(history)
    const wrapper = mountHistory()
    await flushPromises()

    const claims = wrapper.findAll('[data-test="claim"]').map((c) => c.text())
    expect(claims[0]).toContain('Grace')
    expect(claims[0]).toContain('refused')
    expect(claims[0]).toContain('This claim does not complete the prize yet')
    expect(claims[1]).toContain('Ada')
    expect(claims[1]).toContain('accepted')
  })

  it('shows the winners of each prize, and why the game ended', async () => {
    vi.mocked(fetchGameHistory).mockResolvedValue(history)
    const wrapper = mountHistory()
    await flushPromises()

    expect(wrapper.text()).toContain('The full house was claimed')
    expect(wrapper.text()).toContain('Default')
    const winners = wrapper.findAll('[data-test="winner"]').map((w) => w.text())
    expect(winners).toEqual(['Early five: nobody', 'Full house: Ada'])
  })

  it('says when there is no history', async () => {
    const { GameHistoryError } = await import('../api/games')
    vi.mocked(fetchGameHistory).mockRejectedValue(new GameHistoryError(404))
    const wrapper = mountHistory()
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('There is no stored history for this game')
  })
})

describe('linking to the history from the ended game', () => {
  beforeEach(() => {
    vi.mocked(watchLobby).mockResolvedValue({ ok: true, players: [], prizes: [], claims: [] })
  })

  it('links the host to the history once the game has ended', async () => {
    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 't' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()
    expect(wrapper.find('[data-test="history-link"]').exists()).toBe(false)

    useLobbyStore().endReason = 'host'
    await flushPromises()

    expect(wrapper.get('[data-test="history-link"]').attributes('href')).toBe('/games/ABC123/history')
  })

  it('links a player to the history once the game has ended', async () => {
    const wrapper = mount(PlayerLobbyView, {
      props: { code: 'ABC123' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()
    expect(wrapper.find('[data-test="history-link"]').exists()).toBe(false)

    useLobbyStore().endReason = 'full_house'
    await flushPromises()

    expect(wrapper.get('[data-test="history-link"]').attributes('href')).toBe('/games/ABC123/history')
  })
})
