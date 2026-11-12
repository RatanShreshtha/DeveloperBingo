import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PlayerLobbyView from './PlayerLobbyView.vue'
import { joinedAda, startFresh } from './testSetup'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

describe('PlayerLobbyView draws', () => {
  it('shows every drawn topic with its explanation, in order', async () => {
    await joinedAda(fake, {
      status: 'started',
      draws: [
        { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' },
        { position: 2, name: 'JSON', explanation: 'A lightweight data format.' },
      ],
    })

    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    const history = wrapper.findAll('[data-test="draw-history"] li').map((li) => li.text())
    expect(history).toHaveLength(2)
    expect(history[0]).toContain('Algorithm')
    expect(history[0]).toContain('A finite sequence of steps.')
    expect(history[1]).toContain('JSON')
    expect(history[1]).toContain('A lightweight data format.')
  })

  it('shows a draw the room announces', async () => {
    await joinedAda(fake, { status: 'started' })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    fake.emit('topic_drawn', { position: 1, name: 'Monad', explanation: 'A burrito.' })
    await flushPromises()

    expect(wrapper.text()).toContain('Monad')
  })

  it('says the game is still waiting to start before the host starts it', async () => {
    await joinedAda(fake)
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Waiting for the host to start the game.')
  })

  it('says the game has started once it has', async () => {
    await joinedAda(fake, { status: 'started' })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('The game has started.')
  })
})
