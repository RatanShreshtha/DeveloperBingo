import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { drawTopic, getDrawHistory, onGameStarted, onTopicDrawn, startGame } from '../realtime/socket'
import { useLobbyStore } from './lobby'

vi.mock('../api/games', () => ({
  createGame: vi.fn(),
}))
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

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

  it('keeps the game unstarted and shows the refusal beside the controls', async () => {
    vi.mocked(startGame).mockResolvedValue({ ok: false, error: 'not_host' })
    const store = useLobbyStore()

    await store.start('ABC123', 'wrong-token')

    expect(store.started).toBe(false)
    expect(store.actionError).toBe('This host link is not valid for this game')
    expect(store.error).toBeNull()
  })

  it('records a draw the host makes', async () => {
    vi.mocked(drawTopic).mockResolvedValue({ ok: true, draw: firstDraw })
    const store = useLobbyStore()

    await store.drawNext('ABC123', 'secret-token')

    expect(store.draws).toEqual([firstDraw])
  })

  it('does not record a draw twice when the room also announces the host\'s own draw', async () => {
    vi.mocked(drawTopic).mockResolvedValue({ ok: true, draw: firstDraw })
    const store = useLobbyStore()
    const announced = vi.mocked(onTopicDrawn).mock.calls[0][0]

    await store.drawNext('ABC123', 'secret-token')
    announced(firstDraw)

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

  it('loads the draw history for someone catching up', async () => {
    vi.mocked(getDrawHistory).mockResolvedValue({ ok: true, draws: [firstDraw] })
    const store = useLobbyStore()

    await store.loadDrawHistory('ABC123')

    expect(getDrawHistory).toHaveBeenCalledWith('ABC123')
    expect(store.draws).toEqual([firstDraw])
    expect(store.started).toBe(true)
  })

  it('keeps a refused draw separate from the lobby error', async () => {
    vi.mocked(drawTopic).mockResolvedValue({ ok: false, error: 'no_topics_left' })
    const store = useLobbyStore()

    await store.drawNext('ABC123', 'secret-token')

    expect(store.actionError).toBe('Every topic has already been drawn')
    expect(store.error).toBeNull()
  })
})
