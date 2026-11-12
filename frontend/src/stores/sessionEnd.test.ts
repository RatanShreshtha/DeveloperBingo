import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { useHostSession } from './session'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

const link = { code: 'ABC123', host_token: 'secret-token' }

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

describe('session store when the game ends', () => {
  it('is not ended to begin with', () => {
    const store = useHostSession()

    expect(store.ended).toBe(false)
    expect(store.endReason).toBeNull()
  })

  it('records that the game ended, and why, when the room announces it', () => {
    const store = useHostSession()

    fake.emit('game_ended', { reason: 'full_house' })

    expect(store.ended).toBe(true)
    expect(store.endReason).toBe('full_house')
  })

  it('ends the game when the host ends it', async () => {
    fake.answer('end_game', { ok: true })
    const store = useHostSession()

    await store.end(link)

    expect(fake.payloads('end_game')).toEqual([link])
    expect(store.ended).toBe(true)
    expect(store.endReason).toBe('host')
  })

  it('stays running and says why when ending the game is refused', async () => {
    fake.answer('end_game', { ok: false, error: 'not_host' })
    const store = useHostSession()

    await store.end(link)

    expect(store.ended).toBe(false)
    expect(store.actionError).toBe('This host link is not valid for this game')
  })
})
