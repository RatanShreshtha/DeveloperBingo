import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { hostSnapshot } from '../testing/snapshots'
import { useHostSession } from './session'

const link = { code: 'ABC123', host_token: 'secret' }
const refused = { player: 'Ada', prize: 'early_five', accepted: false, error: 'claim_not_valid' } as const
const accepted = { player: 'Grace', prize: 'top_line', accepted: true, error: null } as const

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

describe('session store claim log', () => {
  it('lists no claims until the host hears of one', () => {
    expect(useHostSession().claims).toEqual([])
  })

  it('adds each claim the server logs, in order', () => {
    const store = useHostSession()

    fake.emit('claim_logged', refused)
    fake.emit('claim_logged', accepted)

    expect(store.claims).toEqual([refused, accepted])
  })

  it('takes the claims so far from the watch acknowledgement, so a reconnecting host sees them', async () => {
    fake.answer('watch_lobby', hostSnapshot({ claims: [refused, accepted] }))
    const store = useHostSession()

    await store.watchAsHost(link)

    expect(store.claims).toEqual([refused, accepted])
  })
})
