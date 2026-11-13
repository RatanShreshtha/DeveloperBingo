import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { hostSnapshot, playerSnapshot } from '../testing/snapshots'
import { UNREACHABLE } from '../utils/errors'
import { useHostSession, usePlayerSession } from './session'

const link = { code: 'ABC123', host_token: 'secret-token' }
const unreachable = () => Promise.reject(new Error('operation has timed out'))

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

async function watching() {
  fake.answer('watch_lobby', hostSnapshot({ status: 'started' }))
  const store = useHostSession()
  await store.watchAsHost(link)
  return store
}

describe('host actions when the server cannot be reached', () => {
  it.each([
    ['start_game', (s: ReturnType<typeof useHostSession>) => s.start()],
    ['draw_topic', (s: ReturnType<typeof useHostSession>) => s.drawNext()],
    ['end_game', (s: ReturnType<typeof useHostSession>) => s.end()],
  ] as const)('says so beside the controls and changes nothing when %s fails', async (command, act) => {
    const store = await watching()
    fake.answer(command, unreachable)

    await act(store)

    expect(store.actionError).toBe(UNREACHABLE)
    expect(store.error).toBeNull()
    expect(store.ended).toBe(false)
    expect(store.draws).toEqual([])
  })

  it('does nothing before the host is watching: there is no link to act with', async () => {
    const store = useHostSession()

    await store.start()
    await store.drawNext()
    await store.end()

    expect(fake.sent).toEqual([])
  })

  it('acts with the link it is watching with', async () => {
    const store = await watching()
    fake.answer('draw_topic', { ok: false, error: 'no_topics_left' })

    await store.drawNext()

    expect(fake.payloads('draw_topic')).toEqual([link])
  })

  it('fails the page when opening the dashboard cannot reach the server', async () => {
    fake.answer('watch_lobby', unreachable)
    const store = useHostSession()

    await store.watchAsHost(link)

    expect(store.error).toBe(UNREACHABLE)
  })

  it('keeps the dashboard up when winning the connection back cannot reach the server', async () => {
    const store = await watching()
    fake.answer('watch_lobby', unreachable)

    await fake.reconnect()

    expect(store.error).toBeNull()
    expect(store.actionError).toBe(UNREACHABLE)
    expect(store.started).toBe(true)
  })
})

describe('player actions when the server cannot be reached', () => {
  async function joined() {
    fake.answer('join_game', playerSnapshot())
    const store = usePlayerSession()
    await store.join('ABC123', 'Ada')
    return store
  }

  it('leaves the tick as it was and says so', async () => {
    const store = await joined()
    fake.answer('tick_topic', unreachable)

    await store.toggleTick('Algorithm')

    expect(store.ticks).toEqual([])
    expect(store.actionError).toBe(UNREACHABLE)
  })

  it('drops the pending claim and says so', async () => {
    const store = await joined()
    fake.answer('claim_prize', unreachable)

    await store.claimPrize('early_five')

    expect(store.isPending('early_five')).toBe(false)
    expect(store.actionError).toBe(UNREACHABLE)
  })
})
