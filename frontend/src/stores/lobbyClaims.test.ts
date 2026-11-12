import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { onClaimLogged, watchLobby } from '../realtime/socket'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const link = { code: 'ABC123', host_token: 'secret' }
const refused = { player: 'Ada', prize: 'early_five', accepted: false, error: 'claim_not_valid' } as const
const accepted = { player: 'Grace', prize: 'top_line', accepted: true, error: null } as const

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(onClaimLogged).mockReset()
})

describe('lobby store claim log', () => {
  it('lists no claims until the host hears of one', () => {
    expect(useLobbyStore().claims).toEqual([])
  })

  it('adds each claim the server logs, in order', () => {
    const store = useLobbyStore()
    const logged = vi.mocked(onClaimLogged).mock.calls[0][0]

    logged(refused)
    logged(accepted)

    expect(store.claims).toEqual([refused, accepted])
  })

  it('takes the claims so far from the watch acknowledgement, so a reconnecting host sees them', async () => {
    vi.mocked(watchLobby).mockResolvedValue({ ok: true, players: [], prizes: [], claims: [refused, accepted] })
    const store = useLobbyStore()

    await store.watchAsHost(link)

    expect(store.claims).toEqual([refused, accepted])
  })
})
