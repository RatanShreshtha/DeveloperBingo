import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import {
  installFakeTransport,
  type FakeTransport,
} from '../testing/fakeTransport'
import { hostSnapshot, playerSnapshot } from '../testing/snapshots'
import { useHostSession, usePlayerSession } from './session'

const link = { code: 'ABC123', host_token: 'secret' }
const draw = {
  position: 1,
  name: 'Algorithm',
  explanation: 'A finite sequence of steps.',
}

let fake: FakeTransport
beforeEach(() => {
  sessionStorage.clear()
  fake = installFakeTransport()
  setActivePinia(createPinia())
})

describe('role-specific session modules', () => {
  it('shares game state and registers event listeners only once across callers', async () => {
    const host = useHostSession()
    const anotherHost = useHostSession()
    const player = usePlayerSession()
    const anotherPlayer = usePlayerSession()
    fake.answer(
      'join_game',
      playerSnapshot({ status: 'started', draws: [draw] }),
    )

    await player.join('ABC123', 'Ada')
    fake.emit('topic_drawn', {
      position: 2,
      name: 'Cache',
      explanation: 'A temporary store.',
    })
    fake.emit('claim_logged', {
      player: 'Ada',
      prize: 'early_five',
      accepted: true,
      error: null,
    })

    expect(host.started).toBe(true)
    expect(anotherPlayer.draws).toEqual(player.draws)
    expect(host.draws).toEqual(player.draws)
    expect(host.draws).toHaveLength(2)
    expect(anotherHost.claims).toEqual([
      { player: 'Ada', prize: 'early_five', accepted: true, error: null },
    ])
    expect(anotherPlayer.player).toEqual({ code: 'ABC123', name: 'Ada' })
    expect(player).not.toHaveProperty('watchAsHost')
    expect(host).not.toHaveProperty('claimPrize')
  })

  it('recovers the player only once when both role modules have been used', async () => {
    const host = useHostSession()
    const player = usePlayerSession()
    fake.answer('watch_lobby', hostSnapshot())
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'token' }))
    await host.watchAsHost(link)
    await player.join('ABC123', 'Ada')

    await fake.reconnect()

    expect(fake.payloads('watch_lobby')).toEqual([link])
    expect(fake.payloads('join_game')).toEqual([
      { code: 'ABC123', name: 'Ada', rejoin_token: null },
      { code: 'ABC123', name: 'Ada', rejoin_token: 'token' },
    ])
  })

  it('reconnects the host once the player has been replaced, if the tab also watches as host', async () => {
    const host = useHostSession()
    const player = usePlayerSession()
    fake.answer('watch_lobby', hostSnapshot())
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'token' }))
    await host.watchAsHost(link)
    await player.join('ABC123', 'Ada')
    fake.emit('replaced', {})

    await fake.reconnect()

    expect(fake.payloads('join_game')).toEqual([
      { code: 'ABC123', name: 'Ada', rejoin_token: null },
    ])
    expect(fake.payloads('watch_lobby')).toEqual([link, link])
  })

  it('recovers the host once even when both role modules are accessed', async () => {
    const host = useHostSession()
    useHostSession()
    usePlayerSession()
    fake.answer('watch_lobby', hostSnapshot())
    await host.watchAsHost(link)
    fake.answer('watch_lobby', hostSnapshot({ window_open: true }))

    await fake.reconnect()

    expect(fake.payloads('watch_lobby')).toEqual([link, link])
    expect(host.windowOpen).toBe(true)
  })
})
