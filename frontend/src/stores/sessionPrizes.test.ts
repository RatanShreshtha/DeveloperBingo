import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { playerSnapshot } from '../testing/snapshots'
import { useSessionStore } from './session'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  fake.answer('join_game', playerSnapshot())
  setActivePinia(createPinia())
})

describe('session store prizes', () => {
  it('lists no prizes until the server sends the board', () => {
    expect(useSessionStore().prizes).toEqual([])
  })

  it('shows who was awarded a prize when the room announces it', async () => {
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')

    fake.emit('prize_awarded', { prize: 'early_five', awarded_to: ['Ada'] })

    expect(store.prizes).toEqual([{ prize: 'early_five', awarded_to: ['Ada'] }])
  })

  it('restores the prize board a player gets when they join', async () => {
    fake.answer('join_game', playerSnapshot({ prizes: [{ prize: 'early_five', awarded_to: ['Grace'] }] }))
    const store = useSessionStore()

    await store.join('ABC123', 'Ada')

    expect(store.prizes).toEqual([{ prize: 'early_five', awarded_to: ['Grace'] }])
  })

  it('sends a claim for the prize, which waits until its window settles', async () => {
    fake.answer('claim_prize', { ok: true, waiting: true })
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(fake.payloads('claim_prize')).toEqual([{ prize: 'early_five' }])
    expect(store.isPending('early_five')).toBe(true)

    fake.emit('claim_settled', { prize: 'early_five', accepted: true, error: null })

    expect(store.isPending('early_five')).toBe(false)
    expect(store.actionError).toBeNull()
  })

  it('shows why a waiting claim was refused when its window settles', async () => {
    fake.answer('claim_prize', { ok: true, waiting: true })
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')
    await store.claimPrize('early_five')

    fake.emit('claim_settled', { prize: 'early_five', accepted: false, error: 'game_ended' })

    expect(store.isPending('early_five')).toBe(false)
    expect(store.actionError).toBe('The game has ended')
  })

  it('stays settled when the window closes before the acknowledgement arrives', async () => {
    const store = useSessionStore()
    fake.answer('claim_prize', () => {
      fake.emit('claim_settled', { prize: 'early_five', accepted: true, error: null })
      return { ok: true, waiting: true }
    })
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(store.isPending('early_five')).toBe(false)
  })

  it('shows why a claim was refused, and changes no prize', async () => {
    fake.answer('claim_prize', { ok: false, error: 'claim_not_valid' })
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(store.actionError).toBe('This claim does not complete the prize yet')
    expect(store.prizes).toEqual([{ prize: 'early_five', awarded_to: [] }])
  })

  it('says a prize is taken when someone else has been awarded it', async () => {
    fake.answer('claim_prize', { ok: false, error: 'prize_taken' })
    const store = useSessionStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(store.actionError).toBe('Someone has already been awarded this prize')
  })
})
