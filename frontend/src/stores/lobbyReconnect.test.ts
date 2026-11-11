import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { joinGame, onReconnect } from '../realtime/socket'
import { useLobbyStore } from './lobby'
import { joinedResult } from '../testing/joinMock'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const ticket = [
  ['Algorithm', null, 'JSON', null, null, 'Monad', null, null, 'Pi'],
  [null, 'Cache', null, null, 'Agile', null, 'Rust', null, null],
  ['Pointer', null, null, 'Tech debt', null, null, null, 'Babel', null],
]

// The handler the store registered for "the socket reconnected".
function reconnect(): Promise<void> {
  const calls = vi.mocked(onReconnect).mock.calls
  return Promise.resolve(calls[calls.length - 1][0]())
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(joinGame).mockReset()
  vi.mocked(onReconnect).mockReset()
})

describe('lobby store after the socket reconnects', () => {
  it('joins again with the same code and name and takes back its ticks and prizes', async () => {
    vi.mocked(joinGame).mockResolvedValue(joinedResult(ticket))
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')
    vi.mocked(joinGame).mockClear()
    vi.mocked(joinGame).mockResolvedValue(
      joinedResult(ticket, ['Pi'], { early_five: 'Grace' }),
    )

    await reconnect()

    expect(joinGame).toHaveBeenCalledWith('ABC123', 'Ada')
    expect(store.ticks).toEqual(['Pi'])
    expect(store.prizes).toEqual({ early_five: 'Grace' })
  })

  it('does nothing when no player has joined yet', async () => {
    const store = useLobbyStore()

    await reconnect()

    expect(joinGame).not.toHaveBeenCalled()
    expect(store.ticket).toBeNull()
  })

  it('keeps the ticket on screen if the rejoin is refused', async () => {
    vi.mocked(joinGame).mockResolvedValue(joinedResult(ticket))
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')
    vi.mocked(joinGame).mockResolvedValue({ ok: false, error: 'name_taken' })

    await reconnect()

    expect(store.ticket).toEqual(ticket)
    expect(store.actionError).toBe('That name is already taken in this game')
  })
})
