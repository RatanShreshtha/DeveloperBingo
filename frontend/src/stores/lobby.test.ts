import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { joinGame } from '../realtime/socket'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const ticket = [
  ['Algorithm', null, 'JSON', null, null, 'Monad', null, null, 'Pi'],
  [null, 'Cache', null, null, 'Agile', null, 'Rust', null, null],
  ['Pointer', null, null, 'Tech debt', null, null, null, 'Babel', null],
]

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(joinGame).mockReset()
})

describe('lobby store', () => {
  it('keeps the ticket the server dealt when the player joins', async () => {
    vi.mocked(joinGame).mockResolvedValue({ ok: true, ticket, ticks: [] })
    const store = useLobbyStore()

    const joined = await store.join('ABC123', 'Ada')

    expect(joined).toBe(true)
    expect(store.ticket).toEqual(ticket)
  })

  it('leaves no ticket behind when the join is refused', async () => {
    vi.mocked(joinGame).mockResolvedValue({ ok: false, error: 'name_taken' })
    const store = useLobbyStore()

    await store.join('ABC123', 'Ada')

    expect(store.ticket).toBeNull()
  })
})
