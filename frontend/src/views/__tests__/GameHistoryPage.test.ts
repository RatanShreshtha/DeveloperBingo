import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchGameHistory } from '../../api/games'
import { HttpError } from '../../api/request'
import { hostSnapshot } from '../../testing/snapshots'
import GameHistoryView from '../GameHistoryPage.vue'
import HostView from '../HostPage.vue'
import PlayerLobbyView from '../PlayerPage.vue'
import { makePlugins } from '../../testing/testRouter'
import { joinedAda, startFresh } from '../../testing/testSetup'

vi.mock('../../api/games', async () => (await import('../../testing/apiMock')).apiGamesMock())
vi.mock('../../api/pools', () => ({ fetchDefaultPool: vi.fn(async () => ({ columns: [] })) }))

const history = {
  code: 'ABC123',
  end_reason: 'full_house' as const,
  pool_name: 'Default',
  draws: [
    { position: 1, name: 'Cache', explanation: 'Keeps results close' },
    { position: 2, name: 'Index', explanation: 'Speeds lookups' },
  ],
  claims: [
    { player: 'Grace', prize: 'early_five' as const, accepted: false, error: 'claim_not_valid' as const },
    { player: 'Ada', prize: 'full_house' as const, accepted: true, error: null },
  ],
  prizes: [
    { prize: 'early_five' as const, awarded_to: [] },
    { prize: 'full_house' as const, awarded_to: ['Ada'] },
  ],
}

beforeEach(() => {
  startFresh()
  vi.mocked(fetchGameHistory).mockReset()
})

function mountHistory() {
  return mount(GameHistoryView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
}

describe('GameHistoryView', () => {
  it('shows the draws newest first with their original positions and explanations', async () => {
    vi.mocked(fetchGameHistory).mockResolvedValue(history)
    const wrapper = mountHistory()
    await flushPromises()

    expect(fetchGameHistory).toHaveBeenCalledWith('ABC123')
    const draws = wrapper.findAll('[data-test="draw"]').map((d) => d.text())
    expect(draws).toEqual(['2. Index: Speeds lookups', '1. Cache: Keeps results close'])
    expect(history.draws.map((draw) => draw.position)).toEqual([1, 2])
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
    vi.mocked(fetchGameHistory).mockRejectedValue(new HttpError(new Response(null, { status: 404 })))
    const wrapper = mountHistory()
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('There is no stored history for this game')
  })

  it('says when history is unavailable', async () => {
    vi.mocked(fetchGameHistory).mockRejectedValue(new HttpError(new Response(null, { status: 503 })))
    const wrapper = mountHistory()
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Game history is unavailable right now. Try again shortly.')
  })

  it('reports a network failure', async () => {
    vi.mocked(fetchGameHistory).mockRejectedValue(new TypeError('network'))
    const wrapper = mountHistory()
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('Could not load the game history')
  })
})

describe('linking to the history from the ended game', () => {
  let fake: ReturnType<typeof startFresh>

  beforeEach(() => {
    fake = startFresh()
    fake.answer('watch_lobby', hostSnapshot({ status: 'started' }))
  })

  it('links the host to the history once the game has ended', async () => {
    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 't' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()
    expect(wrapper.find('[data-test="history-link"]').exists()).toBe(false)

    fake.emit('game_ended', { reason: 'host' })
    await flushPromises()

    expect(wrapper.get('[data-test="history-link"]').attributes('href')).toBe('/games/ABC123/history')
  })

  it('links a player to the history once the game has ended', async () => {
    await joinedAda(fake, { status: 'started' })
    const wrapper = mount(PlayerLobbyView, {
      props: { code: 'ABC123' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()
    expect(wrapper.find('[data-test="history-link"]').exists()).toBe(false)

    fake.emit('game_ended', { reason: 'full_house' })
    await flushPromises()

    expect(wrapper.get('[data-test="history-link"]').attributes('href')).toBe('/games/ABC123/history')
  })
})
