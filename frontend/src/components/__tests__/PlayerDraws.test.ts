import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import PlayerLobbyView from '../../views/PlayerPage.vue'
import { joinedAda, startFresh } from '../../testing/testSetup'

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

describe('PlayerLobbyView draws', () => {
  it('shows every drawn topic with its explanation, newest first', async () => {
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
    expect(history[0]).toContain('JSON')
    expect(history[0]).toContain('A lightweight data format.')
    expect(history[1]).toContain('Algorithm')
    expect(history[1]).toContain('A finite sequence of steps.')
  })

  it('orders live draws by position without changing the stored draw order', async () => {
    const store = await joinedAda(fake, {
      status: 'started',
      draws: [{ position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' }],
    })
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    fake.emit('topic_drawn', { position: 3, name: 'Monad', explanation: 'A burrito.' })
    fake.emit('topic_drawn', { position: 2, name: 'JSON', explanation: 'A data format.' })
    await flushPromises()

    const history = wrapper.findAll('[data-test="draw-history"] li').map((li) => li.text())
    expect(history).toEqual(['3. Monad: A burrito.', '2. JSON: A data format.', '1. Algorithm: A finite sequence of steps.'])
    expect(store.draws.map((draw) => draw.name)).toEqual(['Algorithm', 'Monad', 'JSON'])
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
