import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { claimPrize, joinGame, onPrizeAwarded } from '../realtime/socket'
import { joinedResult } from '../testing/joinMock'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

const ticket = [['Algorithm', null, 'JSON']]

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(claimPrize).mockReset()
  vi.mocked(joinGame).mockResolvedValue(joinedResult(ticket))
})

describe('lobby store prizes', () => {
  it('starts with the early five prize open', () => {
    const store = useLobbyStore()

    expect(store.prizes).toEqual({ early_five: null })
  })

  it('shows who won a prize when the room announces it', () => {
    const store = useLobbyStore()
    const announced = vi.mocked(onPrizeAwarded).mock.calls[0][0]

    announced({ prize: 'early_five', winner: 'Ada' })

    expect(store.prizes.early_five).toBe('Ada')
  })

  it('restores the prize board a player gets when they join', async () => {
    vi.mocked(joinGame).mockResolvedValue(joinedResult(ticket, [], { early_five: 'Grace' }))
    const store = useLobbyStore()

    await store.join('ABC123', 'Ada')

    expect(store.prizes.early_five).toBe('Grace')
  })

  it('sends a claim for the player and prize', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: true })
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(claimPrize).toHaveBeenCalledWith({ code: 'ABC123', name: 'Ada' }, 'early_five')
  })

  it('shows why a claim was refused, and changes no prize', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: false, error: 'not_won' })
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(store.actionError).toBe('This claim does not win the prize yet')
    expect(store.prizes.early_five).toBeNull()
  })

  it('says a prize is taken when someone else has won it', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: false, error: 'prize_taken' })
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(store.actionError).toBe('Someone has already won this prize')
  })
})
