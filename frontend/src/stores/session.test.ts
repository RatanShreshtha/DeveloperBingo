import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { playerSnapshot } from '../testing/snapshots'
import { useSessionStore } from './session'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

const ticket = [
  ['Algorithm', null, 'JSON', null, null, 'Monad', null, null, 'Pi'],
  [null, 'Cache', null, null, 'Agile', null, 'Rust', null, null],
  ['Pointer', null, null, 'Tech debt', null, null, null, 'Babel', null],
]

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

describe('session store', () => {
  it('keeps the ticket the server dealt when the player joins', async () => {
    fake.answer('join_game', playerSnapshot({ ticket }))
    const store = useSessionStore()

    const joined = await store.join('ABC123', 'Ada')

    expect(joined).toBe(true)
    expect(store.ticket).toEqual(ticket)
  })

  it('leaves no ticket behind when the join is refused', async () => {
    fake.answer('join_game', { ok: false, error: 'name_taken' })
    const store = useSessionStore()

    await store.join('ABC123', 'Ada')

    expect(store.ticket).toBeNull()
  })
})
