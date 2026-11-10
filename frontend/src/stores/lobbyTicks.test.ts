import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { joinGame, tickTopic, untickTopic } from '../realtime/socket'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const ticket = [['Algorithm', null, 'JSON']]

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

    expect(store.playerCode).toBe('ABC123')
    expect(store.playerName).toBe('Ada')
  })

  it('ticks a topic and keeps the ticks the server reports', async () => {
    vi.mocked(tickTopic).mockResolvedValue({ ok: true, ticked: ['Algorithm'] })
    const store = await joinAsAda()

    await store.toggleTick('Algorithm')

    expect(tickTopic).toHaveBeenCalledWith('ABC123', 'Ada', 'Algorithm')
    expect(store.ticked).toEqual(['Algorithm'])
  })

  it('unticks a topic that is already ticked', async () => {
    vi.mocked(tickTopic).mockResolvedValue({ ok: true, ticked: ['Algorithm'] })
    vi.mocked(untickTopic).mockResolvedValue({ ok: true, ticked: [] })
    const store = await joinAsAda()
    await store.toggleTick('Algorithm')

    await store.toggleTick('Algorithm')

    expect(untickTopic).toHaveBeenCalledWith('ABC123', 'Ada', 'Algorithm')
    expect(store.ticked).toEqual([])
  })

  it('shows why a tick was refused and leaves the ticks alone', async () => {
    vi.mocked(tickTopic).mockResolvedValue({ ok: false, error: 'not_drawn' })
    const store = await joinAsAda()

    await store.toggleTick('Algorithm')

    expect(store.actionError).toBe('That topic has not been drawn yet')
    expect(store.ticked).toEqual([])
  })
})
