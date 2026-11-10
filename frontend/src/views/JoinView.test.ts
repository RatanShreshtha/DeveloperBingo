import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { joinGame } from '../realtime/socket'
import { makePlugins, makeRouter } from './testRouter'
import JoinView from './JoinView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  vi.mocked(joinGame).mockReset()
})

async function fillAndSubmit(wrapper: ReturnType<typeof mount>, code: string, name: string) {
  await wrapper.get('input[name="code"]').setValue(code)
  await wrapper.get('input[name="name"]').setValue(name)
  await wrapper.get('form').trigger('submit')
  await flushPromises()
}

describe('JoinView', () => {
  it('moves the player to the lobby after joining', async () => {
    vi.mocked(joinGame).mockResolvedValue({ ok: true, ticket: [[null]] })
    const router = makeRouter()
    const wrapper = mount(JoinView, { global: { plugins: [createPinia(), router] } })

    await fillAndSubmit(wrapper, 'ABC123', 'Ada')

    expect(joinGame).toHaveBeenCalledWith('ABC123', 'Ada')
    expect(router.currentRoute.value.path).toBe('/games/ABC123')
  })

  it('explains that the name is already taken in the game', async () => {
    vi.mocked(joinGame).mockResolvedValue({ ok: false, error: 'name_taken' })
    const wrapper = mount(JoinView, { global: { plugins: makePlugins() } })

    await fillAndSubmit(wrapper, 'ABC123', 'Ada')

    expect(wrapper.text()).toContain('That name is already taken in this game')
  })
})
