import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { savedSessionFor } from '../realtime/savedSession'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { hostSnapshot, playerSnapshot } from '../testing/snapshots'
import { useSessionStore } from './session'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

const link = { code: 'ABC123', host_token: 'secret' }

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

describe('saving the session', () => {
  it('keeps the code, name and rejoin token after the first join', async () => {
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'tok-1' }))

    await useSessionStore().join('ABC123', 'Ada')

    expect(savedSessionFor('ABC123')).toEqual({ code: 'ABC123', name: 'Ada', token: 'tok-1' })
  })

  it('keeps the name the game stored, not the one typed', async () => {
    fake.answer('join_game', playerSnapshot({ name: 'Ada' }))
    const store = useSessionStore()

    await store.join('ABC123', ' ada ')

    expect(store.player).toEqual({ code: 'ABC123', name: 'Ada' })
    expect(savedSessionFor('ABC123')?.name).toBe('Ada')
  })
})

describe('resuming after a reload', () => {
  it('rejoins with the saved token and applies the snapshot, including an ended game and its prize board', async () => {
    sessionStorage.setItem(
      'devbingo:player',
      JSON.stringify({ code: 'ABC123', name: 'Ada', token: 'tok-1' }),
    )
    fake.answer(
      'join_game',
      playerSnapshot({
        status: 'ended',
        end_reason: 'full_house',
        rejoin_token: 'tok-2',
        prizes: [{ prize: 'full_house', awarded_to: ['Grace'] }],
      }),
    )
    const store = useSessionStore()

    const resumed = await store.resume('ABC123')

    expect(resumed).toBe(true)
    expect(fake.payloads('join_game')).toEqual([
      { code: 'ABC123', name: 'Ada', rejoin_token: 'tok-1' },
    ])
    expect(store.ended).toBe(true)
    expect(store.endReason).toBe('full_house')
    expect(store.prizes).toEqual([{ prize: 'full_house', awarded_to: ['Grace'] }])
    expect(savedSessionFor('ABC123')?.token).toBe('tok-2')
  })

  it('returns false and sends nothing when nothing is saved for the game', async () => {
    const store = useSessionStore()

    expect(await store.resume('ABC123')).toBe(false)
    expect(fake.sent).toEqual([])
  })

  it('forgets the saved session when the rejoin is refused', async () => {
    sessionStorage.setItem(
      'devbingo:player',
      JSON.stringify({ code: 'ABC123', name: 'Ada', token: 'tok-1' }),
    )
    fake.answer('join_game', { ok: false, error: 'not_found' })
    const store = useSessionStore()

    expect(await store.resume('ABC123')).toBe(false)

    expect(savedSessionFor('ABC123')).toBeNull()
    expect(store.error).toBe('No game found with that code')
  })
})

describe('reconnecting', () => {
  it('rejoins sending the latest rejoin token', async () => {
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'tok-1' }))
    await useSessionStore().join('ABC123', 'Ada')
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'tok-2' }))
    await fake.reconnect()

    await fake.reconnect()

    const sent = fake.payloads('join_game')
    expect(sent[1]).toMatchObject({ rejoin_token: 'tok-1' })
    expect(sent[2]).toMatchObject({ rejoin_token: 'tok-2' })
  })

  it('has the host watch again and apply the fresh snapshot', async () => {
    fake.answer('watch_lobby', hostSnapshot())
    const store = useSessionStore()
    await store.watchAsHost(link)
    fake.answer(
      'watch_lobby',
      hostSnapshot({
        status: 'started',
        players: ['Ada'],
        pool: { columns: [[{ name: 'Algorithm', explanation: 'x' }]] },
        pool_name: 'Platform Team',
        window_open: true,
      }),
    )

    await fake.reconnect()

    expect(fake.payloads('watch_lobby')).toEqual([link, link])
    expect(store.started).toBe(true)
    expect(store.players).toEqual(['Ada'])
    expect(store.pool).toEqual([[{ name: 'Algorithm', explanation: 'x' }]])
    expect(store.poolName).toBe('Platform Team')
    expect(store.windowOpen).toBe(true)
  })

  it('follows the server as settlement windows open and close', async () => {
    fake.answer('watch_lobby', hostSnapshot())
    const store = useSessionStore()
    await store.watchAsHost(link)

    fake.emit('window_changed', { open: true })
    expect(store.windowOpen).toBe(true)

    fake.emit('window_changed', { open: false })
    expect(store.windowOpen).toBe(false)
  })

  it('keeps showing an open window when a claim is logged while another window is still open', async () => {
    fake.answer('watch_lobby', hostSnapshot({ window_open: true }))
    const store = useSessionStore()
    await store.watchAsHost(link)

    fake.emit('claim_logged', { player: 'Ada', prize: 'early_five', accepted: false, error: 'claim_not_valid' })

    expect(store.windowOpen).toBe(true)
  })
})

describe('being replaced', () => {
  it('clears the player, says so, and no longer rejoins on reconnect', async () => {
    fake.answer('join_game', playerSnapshot())
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')

    fake.emit('replaced', {})
    fake.sent.length = 0
    await fake.reconnect()

    expect(store.replaced).toBe(true)
    expect(store.player).toBeNull()
    expect(savedSessionFor('ABC123')).toBeNull()
    expect(fake.sent).toEqual([])
  })
})

describe('claims pending across a reconnect', () => {
  it('claims again for each pending prize and keeps it pending until the held answer arrives', async () => {
    let answer: (ack: { ok: true }) => void = () => {}
    fake.answer('join_game', playerSnapshot({ pending_claims: ['early_five'] }))
    fake.answer('claim_prize', () => new Promise((resolve) => (answer = resolve)))
    const store = useSessionStore()

    await store.join('ABC123', 'Ada')

    expect(fake.payloads('claim_prize')).toEqual([{ prize: 'early_five' }])
    expect(store.isPending('early_five')).toBe(true)

    answer({ ok: true })
    await vi.waitFor(() => expect(store.isPending('early_five')).toBe(false))
  })

  it('is not cleared by the stale answer of a claim the reconnect abandoned', async () => {
    const answers: ((ack: { ok: true }) => void)[] = []
    fake.answer('join_game', playerSnapshot())
    fake.answer('claim_prize', () => new Promise((resolve) => answers.push(resolve)))
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')
    void store.claimPrize('early_five')
    fake.answer('join_game', playerSnapshot({ pending_claims: ['early_five'] }))

    await fake.reconnect()
    answers[0]({ ok: true })
    await Promise.resolve()
    await Promise.resolve()

    expect(answers).toHaveLength(2)
    expect(store.isPending('early_five')).toBe(true)
    answers[1]({ ok: true })
    await vi.waitFor(() => expect(store.isPending('early_five')).toBe(false))
  })
})

describe('answers to abandoned claims and unreachable servers', () => {
  it('does not show the refusal of a claim the reconnect abandoned', async () => {
    const answers: ((ack: { ok: false; error: 'claim_not_valid' } | { ok: true }) => void)[] = []
    fake.answer('join_game', playerSnapshot())
    fake.answer('claim_prize', () => new Promise((resolve) => answers.push(resolve)))
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')
    void store.claimPrize('early_five')
    fake.answer('join_game', playerSnapshot({ pending_claims: ['early_five'] }))

    await fake.reconnect()
    answers[0]({ ok: false, error: 'claim_not_valid' })
    await Promise.resolve()
    await Promise.resolve()

    expect(store.actionError).toBeNull()
  })

  it('keeps the saved session and says so when the server cannot be reached on a reload', async () => {
    sessionStorage.setItem('devbingo:player', JSON.stringify({ code: 'ABC123', name: 'Ada', token: 'tok-1' }))
    fake.answer('join_game', () => Promise.reject(new Error('timeout')))
    const store = useSessionStore()

    const resumed = await store.resume('ABC123')

    expect(resumed).toBe(false)
    expect(store.error).toBe('Could not reach the server. Check your connection and try again.')
    expect(savedSessionFor('ABC123')).not.toBeNull()
  })
})

describe('after the game ends', () => {
  it('shows that ticks are refused', async () => {
    fake.answer('join_game', playerSnapshot({ status: 'ended', end_reason: 'host' }))
    fake.answer('tick_topic', { ok: false, error: 'game_ended' })
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')

    await store.toggleTick('Algorithm')

    expect(store.actionError).toBe('The game has ended')
    expect(store.ticks).toEqual([])
  })
})
