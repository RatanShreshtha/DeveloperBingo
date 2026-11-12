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

describe('session store after the connection drops and returns', () => {
  it('joins again as the same player and takes back its ticks and prizes', async () => {
    fake.answer('join_game', playerSnapshot({ ticket }))
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')
    fake.answer(
      'join_game',
      playerSnapshot({ ticket, ticks: ['Pi'], prizes: [{ prize: 'early_five', awarded_to: ['Grace'] }] }),
    )

    await fake.reconnect()

    expect(fake.payloads('join_game')[1]).toMatchObject({ code: 'ABC123', name: 'Ada' })
    expect(store.ticks).toEqual(['Pi'])
    expect(store.prizes).toEqual([{ prize: 'early_five', awarded_to: ['Grace'] }])
  })

  it('does nothing when no player has joined yet', async () => {
    const store = useSessionStore()

    await fake.reconnect()

    expect(fake.sent).toEqual([])
    expect(store.ticket).toBeNull()
  })
})
