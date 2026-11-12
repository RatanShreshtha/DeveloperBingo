import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { playerSnapshot } from '../testing/snapshots'
import { makePlugins, makeRouter } from './testRouter'
import { startFresh } from './testSetup'
import JoinView from './JoinView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

async function fillAndSubmit(wrapper: ReturnType<typeof mount>, code: string, name: string) {
  await wrapper.get('input[name="code"]').setValue(code)
  await wrapper.get('input[name="name"]').setValue(name)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

describe('JoinView', () => {
  it('moves the player to the lobby after joining', async () => {
    fake.answer('join_game', playerSnapshot({ ticket: [[null]] }))
    const router = makeRouter()
    const wrapper = mount(JoinView, { global: { plugins: [createPinia(), router] } })

    await fillAndSubmit(wrapper, 'ABC123', 'Ada')

    expect(fake.payloads('join_game')).toEqual([{ code: 'ABC123', name: 'Ada', rejoin_token: null }])
    expect(router.currentRoute.value.path).toBe('/games/ABC123')
  })

  it('keeps the code, name and rejoin token for a reload', async () => {
    fake.answer('join_game', playerSnapshot({ rejoin_token: 'secret' }))
    const wrapper = mount(JoinView, { global: { plugins: makePlugins() } })

    await fillAndSubmit(wrapper, 'ABC123', 'Ada')

    expect(JSON.parse(sessionStorage.getItem('devbingo:player') ?? 'null')).toEqual({
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
})
