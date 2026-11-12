import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchGameHistory, GameHistoryError } from '../api/games'
import { useHistoryStore } from './history'

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

const history = {
  code: 'ABC123',
  reason: 'host' as const,
  pool_name: null,
  draws: [{ position: 1, name: 'Cache', explanation: 'Keeps results close' }],
  claims: [],
  winners: [],
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(fetchGameHistory).mockReset()
})

describe('history store', () => {
  it('starts out empty', () => {
    const store = useHistoryStore()
    expect(store.history).toBeNull()
    expect(store.error).toBeNull()
  })

  it('loads a game by its code', async () => {
    vi.mocked(fetchGameHistory).mockResolvedValue(history)
    const store = useHistoryStore()

    await store.load('ABC123')

    expect(fetchGameHistory).toHaveBeenCalledWith('ABC123')
    expect(store.history).toEqual(history)
    expect(store.error).toBeNull()
  })

  it('says there is no history when the game has none', async () => {
    vi.mocked(fetchGameHistory).mockRejectedValue(new GameHistoryError(404))
    const store = useHistoryStore()

    await store.load('NOPE')

    expect(store.history).toBeNull()
    expect(store.error).toBe('There is no stored history for this game')
  })

  it('says the history is unavailable when the store is down', async () => {
    vi.mocked(fetchGameHistory).mockRejectedValue(new GameHistoryError(503))
    const store = useHistoryStore()

    await store.load('ABC123')

    expect(store.error).toBe('Game history is unavailable right now. Try again shortly.')
  })

  it('reports any other failure generally', async () => {
    vi.mocked(fetchGameHistory).mockRejectedValue(new TypeError('network'))
    const store = useHistoryStore()

    await store.load('ABC123')

    expect(store.error).toBe('Could not load the game history')
  })
})
