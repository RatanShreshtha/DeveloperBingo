import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { playerSnapshot } from '../testing/snapshots'
import { useHostSession, usePlayerSession } from './session'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

const firstDraw = { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' }
const link = { code: 'ABC123', host_token: 'secret-token' }

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

describe('session store game flow', () => {
  it('marks the game as started when the host starts it', async () => {
    fake.answer('start_game', { ok: true })
    const store = useHostSession()

    await store.start(link)

    expect(fake.payloads('start_game')).toEqual([link])
    expect(store.started).toBe(true)
  })

  it('keeps the game unstarted and shows the refusal beside the controls', async () => {
    fake.answer('start_game', { ok: false, error: 'not_host' })
    const store = useHostSession()

    await store.start({ ...link, host_token: 'wrong-token' })

    expect(store.started).toBe(false)
    expect(store.actionError).toBe('This host link is not valid for this game')
    expect(store.error).toBeNull()
  })

  it('records a draw the host makes', async () => {
    fake.answer('draw_topic', { ok: true, draw: firstDraw })
    const store = useHostSession()

    await store.drawNext(link)

    expect(store.draws).toEqual([firstDraw])
  })

  it("does not record a draw twice when the room also announces the host's own draw", async () => {
    fake.answer('draw_topic', { ok: true, draw: firstDraw })
    const store = useHostSession()

    await store.drawNext(link)
    fake.emit('topic_drawn', firstDraw)

    expect(store.draws).toEqual([firstDraw])
  })

  it('appends draws announced by the room, in order', () => {
    const store = useHostSession()

    fake.emit('topic_drawn', firstDraw)
    fake.emit('topic_drawn', { position: 2, name: 'JSON', explanation: 'A text format.' })

    expect(store.draws.map((draw) => draw.name)).toEqual(['Algorithm', 'JSON'])
  })

  it('marks the game started when the room announces it', () => {
    const store = useHostSession()

    fake.emit('game_started', {})

    expect(store.started).toBe(true)
  })

  it('restores status and draws from a snapshot, so a rejoin between the start and the first draw shows started', async () => {
    fake.answer('join_game', playerSnapshot({ status: 'started', draws: [] }))
    const store = usePlayerSession()

    await store.join('ABC123', 'Ada')

    expect(store.started).toBe(true)
    expect(store.draws).toEqual([])
  })

  it('restores the draws made so far from a snapshot', async () => {
    fake.answer('join_game', playerSnapshot({ status: 'started', draws: [firstDraw] }))
    const store = usePlayerSession()

    await store.join('ABC123', 'Ada')

    expect(store.draws).toEqual([firstDraw])
  })

  it('keeps a refused draw separate from the lobby error', async () => {
    fake.answer('draw_topic', { ok: false, error: 'no_topics_left' })
    const store = useHostSession()

    await store.drawNext(link)

    expect(store.actionError).toBe('Every topic has already been drawn')
    expect(store.error).toBeNull()
  })
})
