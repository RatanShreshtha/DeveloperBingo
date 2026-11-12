import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { hostSnapshot } from '../../testing/snapshots'
import { makePlugins } from '../../testing/testRouter'
import { startFresh } from '../../testing/testSetup'
import HostView from '../HostPage.vue'

vi.mock('../../api/games', async () => (await import('../../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

function mountHost(token = 'secret-token') {
  return mount(HostView, { props: { code: 'ABC123', token }, global: { plugins: makePlugins() } })
}

describe('HostView', () => {
  it('shows the pool the game was created with as columns of topics with their explanations', async () => {
    fake.answer(
      'watch_lobby',
      hostSnapshot({
        pool_name: 'Platform Team',
        pool: {
          columns: [
            [{ name: 'Algorithm', explanation: 'A finite sequence of steps.' }],
            [{ name: 'JSON', explanation: 'A lightweight data format.' }],
          ],
        },
      }),
    )

    const wrapper = mountHost()
    await flushPromises()

    expect(wrapper.text()).toContain('Platform Team')
    expect(wrapper.text()).toContain('Column 1')
    expect(wrapper.text()).toContain('Algorithm')
    expect(wrapper.text()).toContain('A finite sequence of steps.')
    expect(wrapper.text()).toContain('Column 2')
    expect(wrapper.text()).toContain('JSON')
  })

  it('shows the players the server reports for the lobby', async () => {
    fake.answer('watch_lobby', hostSnapshot({ players: ['Ada'] }))

    const wrapper = mountHost()
    await flushPromises()

    expect(fake.payloads('watch_lobby')).toEqual([{ code: 'ABC123', host_token: 'secret-token' }])
    expect(wrapper.text()).toContain('Ada')
  })

  it('updates the list when a lobby update arrives', async () => {
    fake.answer('watch_lobby', hostSnapshot({ players: ['Ada'] }))

    const wrapper = mountHost()
    await flushPromises()
    fake.emit('lobby_updated', { players: ['Ada', 'Grace'] })
    await flushPromises()

    expect(wrapper.text()).toContain('Grace')
  })

  it('explains when the host link is not valid for the game', async () => {
    fake.answer('watch_lobby', { ok: false, error: 'not_host' })

    const wrapper = mountHost()
    await flushPromises()

    expect(wrapper.text()).toContain('This host link is not valid for this game')
  })
})
