import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { endGame, onGameEnded } from '../realtime/socket'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const link = { code: 'ABC123', host_token: 'secret-token' }

// The handler the store registered for "the game ended".
function announceEnd(reason: 'full_house' | 'host') {
  const calls = vi.mocked(onGameEnded).mock.calls
  calls[calls.length - 1][0]({ reason })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(onGameEnded).mockReset()
  vi.mocked(endGame).mockReset()
})

describe('lobby store when the game ends', () => {
  it('is not ended to begin with', () => {
    const store = useLobbyStore()

    expect(store.ended).toBe(false)
    expect(store.endReason).toBeNull()
  })

  it('records that the game ended, and why, when the room announces it', () => {
    const store = useLobbyStore()

    announceEnd('full_house')

    expect(store.ended).toBe(true)
    expect(store.endReason).toBe('full_house')
  })

  it('ends the game when the host ends it', async () => {
    vi.mocked(endGame).mockResolvedValue({ ok: true })
    const store = useLobbyStore()

    await store.end(link)

    expect(endGame).toHaveBeenCalledWith(link)
    expect(store.ended).toBe(true)
    expect(store.endReason).toBe('host')
  })

  it('stays running and says why when ending the game is refused', async () => {
    vi.mocked(endGame).mockResolvedValue({ ok: false, error: 'not_host' })
    const store = useLobbyStore()

    await store.end(link)

    expect(store.ended).toBe(false)
    expect(store.actionError).toBe('This host link is not valid for this game')
  })
})
