import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { hostSnapshot } from '../../../testing/snapshots'
import { makePlugins } from '../../../testing/testRouter'
import { startFresh } from '../../../testing/testSetup'
import HostView from './HostPage.vue'

vi.mock('../../../api/games', async () => (await import('../../../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
  fake.answer('watch_lobby', hostSnapshot({ players: ['Ada'] }))
})

function mountHost() {
  return mount(HostView, {
    props: { code: 'ABC123', token: 'secret-token' },
    global: { plugins: makePlugins() },
  })
}

async function startTheGame(wrapper: ReturnType<typeof mountHost>) {
  fake.answer('start_game', { ok: true })
  await wrapper.get('[data-test="start-game"]').trigger('click')
  await flushPromises()
}

describe('HostView game flow', () => {
  it('starts the game when the host presses Start', async () => {
    const wrapper = mountHost()
    await flushPromises()

    await startTheGame(wrapper)

    expect(fake.payloads('start_game')).toEqual([{ code: 'ABC123', host_token: 'secret-token' }])
    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(true)
  })

  it('shows Draw topic, not Start game, when the host reloads a started game with no draws yet', async () => {
    fake.answer('watch_lobby', hostSnapshot({ status: 'started' }))
    const wrapper = mountHost()
    await flushPromises()

    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(true)
  })

  it('shows the drawn topic and its explanation after a draw', async () => {
    fake.answer('draw_topic', {
      ok: true,
      draw: { position: 1, name: 'Algorithm', explanation: 'A finite sequence of steps.' },
    })
    const wrapper = mountHost()
    await flushPromises()
    await startTheGame(wrapper)

    await wrapper.get('[data-test="draw-topic"]').trigger('click')
    await flushPromises()

    expect(fake.payloads('draw_topic')).toEqual([{ code: 'ABC123', host_token: 'secret-token' }])
    expect(wrapper.text()).toContain('Algorithm')
    expect(wrapper.text()).toContain('A finite sequence of steps.')
  })

  it('shows the newest draw first after the host draws', async () => {
    fake.answer('watch_lobby', hostSnapshot({
      status: 'started',
      draws: [{ position: 1, name: 'Algorithm', explanation: 'First draw.' }],
    }))
    fake.answer('draw_topic', {
      ok: true,
      draw: { position: 2, name: 'JSON', explanation: 'Second draw.' },
    })
    const wrapper = mountHost()
    await flushPromises()

    await wrapper.get('[data-test="draw-topic"]').trigger('click')
    await flushPromises()

    const draws = wrapper.findAll('[data-test="draw-history"] li').map((li) => li.text())
    expect(draws).toEqual(['JSON: Second draw.', 'Algorithm: First draw.'])
  })

  it('keeps the Draw control and explains a refused draw', async () => {
    fake.answer('draw_topic', { ok: false, error: 'no_topics_left' })
    const wrapper = mountHost()
    await flushPromises()
    await startTheGame(wrapper)

    await wrapper.get('[data-test="draw-topic"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Every topic has already been drawn')
  })

  it('shows no game controls when the host link is refused', async () => {
    fake.answer('watch_lobby', { ok: false, error: 'not_host' })
    const wrapper = mountHost()
    await flushPromises()

    expect(wrapper.find('[data-test="start-game"]').exists()).toBe(false)
    expect(wrapper.find('[data-test="draw-topic"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('This host link is not valid for this game')
  })

  it('says a claim is being settled while the snapshot reports an open window', async () => {
    fake.answer('watch_lobby', hostSnapshot({ status: 'started', window_open: true }))
    const wrapper = mountHost()
    await flushPromises()

    expect(wrapper.get('[data-test="window-open"]').text()).toContain('A claim is being settled')
  })

  it('stops saying so once the server says no window is open', async () => {
    fake.answer('watch_lobby', hostSnapshot({ status: 'started', window_open: true }))
    const wrapper = mountHost()
    await flushPromises()

    fake.emit('window_changed', { open: false })
    await flushPromises()

    expect(wrapper.find('[data-test="window-open"]').exists()).toBe(false)
  })
})
