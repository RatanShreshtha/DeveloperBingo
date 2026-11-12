import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { playerSnapshot } from '../testing/snapshots'
import { usePlayerSession } from './session'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

const ada = { code: 'ABC123', name: 'Ada' }

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  fake.answer('join_game', playerSnapshot())
  setActivePinia(createPinia())
})

async function joinAsAda() {
  const store = usePlayerSession()
  await store.join('ABC123', 'Ada')
  return store
}

describe('session store ticks', () => {
  it('restores the ticks the server returns when a dropped player rejoins', async () => {
    fake.answer('join_game', playerSnapshot({ ticks: ['Algorithm'] }))
    const store = await joinAsAda()

    expect(store.ticks).toEqual(['Algorithm'])
  })

  it('remembers who the player is when they join', async () => {
    const store = await joinAsAda()

    expect(store.player).toEqual(ada)
  })

  it("adds a topic to the player's ticks once the server accepts the tick", async () => {
    fake.answer('tick_topic', { ok: true })
    const store = await joinAsAda()

    await store.toggleTick('Algorithm')

    expect(fake.payloads('tick_topic')).toEqual([{ topic: 'Algorithm' }])
    expect(store.ticks).toEqual(['Algorithm'])
  })

  it('removes a topic from the ticks once the server accepts the untick', async () => {
    fake.answer('tick_topic', { ok: true })
    fake.answer('untick_topic', { ok: true })
    const store = await joinAsAda()
    await store.toggleTick('Algorithm')

    await store.toggleTick('Algorithm')

    expect(fake.payloads('untick_topic')).toEqual([{ topic: 'Algorithm' }])
    expect(store.ticks).toEqual([])
  })

  it('shows why a tick was refused and leaves the ticks alone', async () => {
    fake.answer('tick_topic', { ok: false, error: 'not_drawn' })
    const store = await joinAsAda()

    await store.toggleTick('Algorithm')

    expect(store.actionError).toBe('That topic has not been drawn yet')
    expect(store.ticks).toEqual([])
  })

  it('refuses ticks once the game has ended and shows why', async () => {
    fake.answer('tick_topic', { ok: false, error: 'game_ended' })
    const store = await joinAsAda()
    fake.emit('game_ended', { reason: 'host' })

    await store.toggleTick('Algorithm')

    expect(store.actionError).toBe('The game has ended')
    expect(store.ticks).toEqual([])
  })
})
