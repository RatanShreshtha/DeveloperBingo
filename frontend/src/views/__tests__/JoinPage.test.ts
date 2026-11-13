import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import { playerSnapshot } from '../../testing/snapshots'
import { makeApplicationPlugins, makePlugins } from '../../testing/testRouter'
import { startFresh } from '../../testing/testSetup'
import JoinView from '../JoinPage.vue'

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

async function fillAndSubmit(
  wrapper: ReturnType<typeof mount>,
  code: string,
  name: string,
) {
  await wrapper.get('input[name="code"]').setValue(code)
  await wrapper.get('input[name="name"]').setValue(name)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

describe('JoinView', () => {
  it('moves the player to the lobby after joining', async () => {
    fake.answer('join_game', playerSnapshot({ ticket: [[null]] }))
    const plugins = makeApplicationPlugins()
    const router = plugins.router
    const wrapper = mount(JoinView, { global: { plugins: [plugins] } })

    await fillAndSubmit(wrapper, 'ABC123', 'Ada')

    expect(fake.payloads('join_game')).toEqual([
      { code: 'ABC123', name: 'Ada', rejoin_token: null },
    ])
    expect(router.currentRoute.value.path).toBe('/games/ABC123')
  })

  it('keeps the code, name and rejoin token for a reload', async () => {
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'secret' }))
    const wrapper = mount(JoinView, { global: { plugins: makePlugins() } })

    await fillAndSubmit(wrapper, 'ABC123', 'Ada')

    expect(
      JSON.parse(sessionStorage.getItem('devbingo:player') ?? 'null'),
    ).toEqual({
      code: 'ABC123',
      name: 'Ada',
      token: 'secret',
    })
  })

  it('explains that the name is already taken in the game', async () => {
    fake.answer('join_game', { ok: false, error: 'name_taken' })
    const wrapper = mount(JoinView, { global: { plugins: makePlugins() } })

    await fillAndSubmit(wrapper, 'ABC123', 'Ada')

    expect(wrapper.text()).toContain('That name is already taken in this game')
  })

  it('does not repeat a refusal from another page', async () => {
    fake.answer('join_game', { ok: false, error: 'name_taken' })
    const plugins = makePlugins()
    const first = mount(JoinView, { global: { plugins } })
    await fillAndSubmit(first, 'ABC123', 'Ada')
    first.unmount()

    const wrapper = mount(JoinView, { global: { plugins } })
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })
})
