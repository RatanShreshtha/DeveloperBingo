import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { hostSnapshot } from '../testing/snapshots'
import HostView from './HostView.vue'
import PlayerLobbyView from './PlayerLobbyView.vue'
import { makePlugins } from './testRouter'
import { joinedAda, startFresh } from './testSetup'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
  fake.answer('watch_lobby', hostSnapshot({ players: ['Ada'], status: 'started' }))
})

function mountHost() {
  return mount(HostView, {
    props: { code: 'ABC123', token: 'secret-token' },
    global: { plugins: makePlugins() },
  })
}

describe('HostView ending the game', () => {
  it('ends the game when the host presses End game', async () => {
    fake.answer('end_game', { ok: true })
    const wrapper = mountHost()
    await flushPromises()

    await wrapper.get('[data-test="end-game"]').trigger('click')
    await flushPromises()

    expect(fake.payloads('end_game')).toEqual([{ code: 'ABC123', host_token: 'secret-token' }])
  })

  it('takes away the start, draw and end controls once the game has ended', async () => {
    const wrapper = mountHost()
    await flushPromises()
    fake.emit('game_ended', { reason: 'host' })
    await flushPromises()

    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="end-game"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('You ended the game')
  })

  it('shows the ended game, not Start game, after the host reloads', async () => {
    fake.answer('watch_lobby', hostSnapshot({ status: 'ended', end_reason: 'full_house' }))
    const wrapper = mountHost()
    await flushPromises()

    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('The game is over: the full house was claimed')
  })
})

describe('PlayerLobbyView when the game ends', () => {
  it('tells the player the full house was claimed and removes the claim buttons', async () => {
    await joinedAda(fake, { status: 'started' })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })
    fake.emit('game_ended', { reason: 'full_house' })
    await flushPromises()

    expect(wrapper.text()).toContain('The game is over: the full house was claimed')
    expect(wrapper.find('[data-test="claim-early_five"]').exists()).toBe(false)
  })

  it('tells the player the host ended the game', async () => {
    await joinedAda(fake, { status: 'started' })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })
    fake.emit('game_ended', { reason: 'host' })
    await flushPromises()

    expect(wrapper.text()).toContain('The host ended the game')
  })

  it('still shows the prizes that were awarded', async () => {
    await joinedAda(fake, {
      status: 'ended',
      end_reason: 'host',
      prizes: [{ prize: 'early_five', awarded_to: ['Grace'] }],
    })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Early five: awarded to Grace')
  })
})
