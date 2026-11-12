import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { saveSession } from '../realtime/savedSession'
import { playerSnapshot } from '../testing/snapshots'
import PlayerLobbyView from './PlayerLobbyView.vue'
import { makePlugins } from './testRouter'
import { joinedAda, startFresh } from './testSetup'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

describe('PlayerLobbyView', () => {
  it('shows the player their own ticket, with empty cells left blank', async () => {
    await joinedAda(fake, {
      ticket: [
        ['Algorithm', null, 'JSON'],
        [null, 'Cache', null],
      ],
    })

    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const cells = wrapper.findAll('[data-test="ticket-cell"]')
    expect(cells).toHaveLength(6)
    expect(wrapper.text()).toContain('Algorithm')
    expect(wrapper.text()).toContain('Cache')
    expect(cells.filter((c) => c.text() === '')).toHaveLength(3)
  })

  describe('after a reload', () => {
    it('rejoins with the saved token and shows the game as it stands', async () => {
      saveSession({ code: 'ABC123', name: 'Ada', token: 'old-token' })
      fake.answer(
        'join_game',
        playerSnapshot({
          status: 'started',
          ticket: [['Algorithm', null, 'JSON']],
          ticks: ['Algorithm'],
          draws: [{ position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' }],
        }),
      )

      const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
      await flushPromises()

      expect(fake.payloads('join_game')).toEqual([
        { code: 'ABC123', name: 'Ada', rejoin_token: 'old-token' },
      ])
      expect(wrapper.text()).toContain('The game has started.')
      expect(wrapper.find('[data-test="join-link"]').exists()).toBe(false)
      expect(wrapper.get('[data-test="tick-cell"]').attributes('aria-pressed')).toBe('true')
      expect(wrapper.findAll('[data-test="draw-history"] li')).toHaveLength(1)
    })

    it('asks the player to join when nothing was saved', async () => {
      const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
      await flushPromises()

      expect(wrapper.get('[data-test="join-link"]').text()).toContain('Join this game')
      expect(fake.sent).toEqual([])
    })

    it('shows the final result of an ended game with the ticks switched off', async () => {
      saveSession({ code: 'ABC123', name: 'Ada', token: 'old-token' })
      fake.answer(
        'join_game',
        playerSnapshot({
          status: 'ended',
          end_reason: 'full_house',
          prizes: [{ prize: 'full_house', awarded_to: ['Grace'] }],
          ticket: [['Algorithm', null, 'JSON']],
          draws: [{ position: 1, name: 'Algorithm', explanation: 'x' }],
        }),
      )

      const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
      await flushPromises()

      expect(wrapper.text()).toContain('The game is over: the full house was claimed')
      expect(wrapper.text()).toContain('Full house: awarded to Grace')
      expect(wrapper.get('[data-test="tick-cell"]').attributes('disabled')).toBeDefined()
    })

    it('asks the player to join when the server refuses the saved session', async () => {
      saveSession({ code: 'ABC123', name: 'Ada', token: 'old-token' })
      fake.answer('join_game', { ok: false, error: 'name_taken' })

      const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
      await flushPromises()

      expect(wrapper.find('[data-test="join-link"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('That name is already taken in this game')
    })
  })

  it('says it is rejoining, not asking to join, while the rejoin is on its way', async () => {
    saveSession({ code: 'ABC123', name: 'Ada', token: 'old-token' })
    fake.answer('join_game', () => new Promise(() => {}))

    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
    await flushPromises()

    expect(wrapper.text()).toContain('Rejoining the game…')
    expect(wrapper.find('[data-test="join-link"]').exists()).toBe(false)
  })

  it('leaves the game and asks the player to join when a reconnect is refused', async () => {
    await joinedAda(fake, { status: 'started' })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' }, global: { plugins: makePlugins() } })
    await flushPromises()
    fake.answer('join_game', { ok: false, error: 'not_found' })

    await fake.reconnect()
    await flushPromises()

    expect(wrapper.text()).toContain('No game found with that code')
    expect(wrapper.get('[data-test="join-link"]').text()).toContain('Join this game')
    expect(wrapper.find('[data-test="tick-cell"]').exists()).toBe(false)
  })

  it('tells the player when another window took their place', async () => {
    await joinedAda(fake, { status: 'started' })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    fake.emit('replaced', {})
    await flushPromises()

    expect(wrapper.get('[data-test="replaced"]').text()).toContain('opened in another window')
    expect(wrapper.find('[data-test="tick-cell"]').exists()).toBe(false)
  })
})
