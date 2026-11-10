import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { drawTopic, onGameStarted, onTopicDrawn, startGame } from '../realtime/socket'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', () => ({
  createGame: vi.fn(),
}))
vi.mock('../realtime/socket', () => ({
  joinGame: vi.fn(),
  watchLobby: vi.fn(),
  onLobbyUpdated: vi.fn(),
  startGame: vi.fn(),
  drawTopic: vi.fn(),
  onGameStarted: vi.fn(),
  onTopicDrawn: vi.fn(),
}))

const firstDraw = { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(startGame).mockReset()
  vi.mocked(drawTopic).mockReset()
})

describe('lobby store game flow', () => {
  it('marks the game as started when the host starts it', async () => {
    vi.mocked(startGame).mockResolvedValue({ ok: true })
    const store = useLobbyStore()

    await store.start('ABC123', 'secret-token')

    expect(startGame).toHaveBeenCalledWith('ABC123', 'secret-token')
    expect(store.started).toBe(true)
  })

  it('keeps the game unstarted and explains the refusal', async () => {
    vi.mocked(startGame).mockResolvedValue({ ok: false, error: 'not_host' })
    const store = useLobbyStore()

    await store.start('ABC123', 'wrong-token')

    expect(store.started).toBe(false)
    expect(store.error).toBe('This host link is not valid for this game')
  })

  it('records a draw the host makes', async () => {
    vi.mocked(drawTopic).mockResolvedValue({ ok: true, draw: firstDraw })
    const store = useLobbyStore()

    await store.drawNext('ABC123', 'secret-token')

    expect(store.draws).toEqual([firstDraw])
  })

  it('appends draws announced by the room, in order', () => {
    const store = useLobbyStore()
    const handler = vi.mocked(onTopicDrawn).mock.calls[0][0]

    handler(firstDraw)
    handler({ position: 2, name: 'JSON', explanation: 'A text format.' })

    expect(store.draws.map((draw) => draw.name)).toEqual(['Algorithm', 'JSON'])
  })

  it('marks the game started when the room announces it', () => {
    const store = useLobbyStore()
    const handler = vi.mocked(onGameStarted).mock.calls[0][0]

    handler()

    expect(store.started).toBe(true)
  })
})
