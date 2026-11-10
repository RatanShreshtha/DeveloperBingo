import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { joinGame, tickTopic, untickTopic } from '../realtime/socket'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const ticket = [['Algorithm', null, 'JSON']]
const ada = { code: 'ABC123', name: 'Ada' }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(tickTopic).mockReset()
  vi.mocked(untickTopic).mockReset()
  vi.mocked(joinGame).mockResolvedValue({ ok: true, ticket })
})

async function joinAsAda() {
  const store = useLobbyStore()
  await store.join('ABC123', 'Ada')
  return store
}

describe('lobby store ticks', () => {
  it('remembers who the player is when they join', async () => {
    const store = await joinAsAda()

    expect(store.player).toEqual(ada)
  })

  it('adds a topic to the player\'s ticks once the server accepts the tick', async () => {
    vi.mocked(tickTopic).mockResolvedValue({ ok: true })
    const store = await joinAsAda()

    await store.toggleTick('Algorithm')

    expect(tickTopic).toHaveBeenCalledWith(ada, 'Algorithm')
    expect(store.ticks).toEqual(['Algorithm'])
  })

  it('removes a topic from the ticks once the server accepts the untick', async () => {
    vi.mocked(tickTopic).mockResolvedValue({ ok: true })
    vi.mocked(untickTopic).mockResolvedValue({ ok: true })
    const store = await joinAsAda()
    await store.toggleTick('Algorithm')

    await store.toggleTick('Algorithm')

    expect(untickTopic).toHaveBeenCalledWith(ada, 'Algorithm')
    expect(store.ticks).toEqual([])
  })

  it('shows why a tick was refused and leaves the ticks alone', async () => {
    vi.mocked(tickTopic).mockResolvedValue({ ok: false, error: 'not_drawn' })
    const store = await joinAsAda()

    await store.toggleTick('Algorithm')

    expect(store.actionError).toBe('That topic has not been drawn yet')
    expect(store.ticks).toEqual([])
  })
})
