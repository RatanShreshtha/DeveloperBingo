import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { savedSessionFor } from '../realtime/savedSession'
import { installFakeTransport, type FakeTransport } from '../testing/fakeTransport'
import { playerSnapshot } from '../testing/snapshots'
import { useSessionStore } from './session'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

const UNREACHABLE = 'Could not reach the server. Check your connection and try again.'
const GONE = 'No game found with that code'

type How = 'fresh' | 'reload' | 'reconnect'
type Answer = 'snapshot' | 'refused' | 'unreachable'

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

function answerJoin(answer: Answer) {
  if (answer === 'snapshot') {
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'tok-new' }))
  } else if (answer === 'refused') {
    fake.answer('join_game', { ok: false, error: 'not_found' })
  } else {
    fake.answer('join_game', () => Promise.reject(new Error('timeout')))
  }
}

/** Joins the way `how` says, with the server answering `answer`. Resolves however the join ends. */
async function enterBy(how: How, answer: Answer) {
  const store = useSessionStore()
  if (how === 'fresh') {
    answerJoin(answer)
    await store.join('ABC123', 'Ada')
  } else if (how === 'reload') {
    sessionStorage.setItem('devbingo:player', JSON.stringify({ code: 'ABC123', name: 'Ada', token: 'tok-1' }))
    answerJoin(answer)
    await store.resume('ABC123')
  } else {
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'tok-1' }))
    await store.join('ABC123', 'Ada')
    answerJoin(answer)
    await fake.reconnect()
  }
  return store
}

const IN = { code: 'ABC123', name: 'Ada' }

// How the join started × how the server answered → what the player is left with.
const cases: [How, Answer, { player: typeof IN | null; error: string | null; actionError: string | null; saved: string | null }][] = [
  ['fresh', 'snapshot', { player: IN, error: null, actionError: null, saved: 'tok-new' }],
  ['fresh', 'refused', { player: null, error: GONE, actionError: null, saved: null }],
  ['fresh', 'unreachable', { player: null, error: UNREACHABLE, actionError: null, saved: null }],
  ['reload', 'snapshot', { player: IN, error: null, actionError: null, saved: 'tok-new' }],
  ['reload', 'refused', { player: null, error: GONE, actionError: null, saved: null }],
  ['reload', 'unreachable', { player: null, error: UNREACHABLE, actionError: null, saved: 'tok-1' }],
  ['reconnect', 'snapshot', { player: IN, error: null, actionError: null, saved: 'tok-new' }],
  ['reconnect', 'refused', { player: null, error: GONE, actionError: null, saved: null }],
  ['reconnect', 'unreachable', { player: IN, error: null, actionError: UNREACHABLE, saved: 'tok-1' }],
]

describe('joining, whichever way it starts', () => {
  it.each(cases)('%s join answered with %s', async (how, answer, expected) => {
    const store = await enterBy(how, answer)

    expect(store.player).toEqual(expected.player)
    expect(store.error).toBe(expected.error)
    expect(store.actionError).toBe(expected.actionError)
    expect(savedSessionFor('ABC123')?.token ?? null).toBe(expected.saved)
    if (expected.player === null) {
      expect(store.ticket).toBeNull()
    }
  })
})
