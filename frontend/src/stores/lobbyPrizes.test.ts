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
  it('lists no prizes until the server sends the board', () => {
    const store = useLobbyStore()

    expect(store.prizes).toEqual([])
  })

  it('shows who was awarded a prize when the room announces it', async () => {
    vi.mocked(joinGame).mockResolvedValue(joinedResult(ticket))
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')
    const announced = vi.mocked(onPrizeAwarded).mock.calls[0][0]

    announced({ prize: 'early_five', awarded_to: ['Ada'] })

    expect(store.prizes).toEqual([{ prize: 'early_five', awarded_to: ['Ada'] }])
  })

  it('restores the prize board a player gets when they join', async () => {
    vi.mocked(joinGame).mockResolvedValue(joinedResult(ticket, [], [{ prize: 'early_five', awarded_to: ['Grace'] }]))
    const store = useLobbyStore()

    await store.join('ABC123', 'Ada')

    expect(store.prizes).toEqual([{ prize: 'early_five', awarded_to: ['Grace'] }])
  })

  it('sends a claim for the player and prize', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: true })
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(claimPrize).toHaveBeenCalledWith('early_five')
  })

  it('shows why a claim was refused, and changes no prize', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: false, error: 'claim_not_valid' })
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(store.actionError).toBe('This claim does not complete the prize yet')
    expect(store.prizes).toEqual([{ prize: 'early_five', awarded_to: [] }])
  })

  it('says a prize is taken when someone else has been awarded it', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: false, error: 'prize_taken' })
    const store = useLobbyStore()
    await store.join('ABC123', 'Ada')

    await store.claimPrize('early_five')

    expect(store.actionError).toBe('Someone has already been awarded this prize')
  })
})
