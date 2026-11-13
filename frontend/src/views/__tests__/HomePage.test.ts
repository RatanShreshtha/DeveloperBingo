import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createGame } from '../../api/games'
import { fetchPools } from '../../api/pools'
import { makePlugins } from '../../testing/testRouter'
import { startFresh } from '../../testing/testSetup'
import HomeView from '../HomePage.vue'

vi.mock('../../api/games', async () => (await import('../../testing/apiMock')).apiGamesMock())
vi.mock('../../api/pools', async () => (await import('../../testing/apiMock')).apiPoolsMock())

beforeEach(() => {
  startFresh()
  vi.mocked(createGame).mockReset()
  vi.mocked(fetchPools).mockReset()
  vi.mocked(fetchPools).mockResolvedValue([{ id: 1, name: 'Default', is_default: true }])
})

async function mountHome() {
  const wrapper = mount(HomeView, { global: { plugins: makePlugins() } })
  await flushPromises()
  return wrapper
}

describe('HomeView', () => {
  it('creates a game without opening a live session', async () => {
    const fake = startFresh()
    const listen = vi.spyOn(fake, 'listen')
    vi.mocked(createGame).mockResolvedValue({ code: 'ABC123', host_token: 'secret-token' })
    const wrapper = await mountHome()

    await wrapper.get('button[data-test="create-game"]').trigger('click')
    await flushPromises()

    expect(createGame).toHaveBeenCalledOnce()
    expect(listen).not.toHaveBeenCalled()
  })

  it('creates a game and shows the code and the private host link', async () => {
    vi.mocked(createGame).mockResolvedValue({ code: 'ABC123', host_token: 'secret-token' })
    const wrapper = await mountHome()

    await wrapper.get('button[data-test="create-game"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('ABC123')
    expect(wrapper.text()).toContain('/host/ABC123?token=secret-token')
  })

  it('creates a game on the default pool unless another is picked', async () => {
    vi.mocked(createGame).mockResolvedValue({ code: 'ABC123', host_token: 't' })
    const wrapper = await mountHome()

    await wrapper.get('button[data-test="create-game"]').trigger('click')

    expect(createGame).toHaveBeenCalledWith({ id: 1, name: 'Default', is_default: true })
  })

  it('has the default pool selected at first, and sends no pool id when it is left alone', async () => {
    vi.mocked(fetchPools).mockResolvedValue([
      { id: 1, name: 'Default', is_default: true },
      { id: 7, name: 'Rustaceans', is_default: false },
    ])
    vi.mocked(createGame).mockResolvedValue({ code: 'ABC123', host_token: 't' })
    const wrapper = await mountHome()

    const select = wrapper.get('select[data-test="pool-picker"]').element as HTMLSelectElement
    expect(select.value).toBe('1')
    expect(select.selectedOptions[0].textContent?.trim()).toBe('Default')

    await wrapper.get('button[data-test="create-game"]').trigger('click')

    expect(createGame).toHaveBeenCalledWith({ id: 1, name: 'Default', is_default: true })
  })

  it('offers every saved pool and creates the game on the one picked', async () => {
    vi.mocked(fetchPools).mockResolvedValue([
      { id: 1, name: 'Default', is_default: true },
      { id: 7, name: 'Rustaceans', is_default: false },
    ])
    vi.mocked(createGame).mockResolvedValue({ code: 'ABC123', host_token: 't' })
    const wrapper = await mountHome()

    const options = wrapper.findAll('select[data-test="pool-picker"] option')
    expect(options.map((option) => option.text())).toEqual(['Default', 'Rustaceans'])

    await wrapper.get('select[data-test="pool-picker"]').setValue('7')
    await wrapper.get('button[data-test="create-game"]').trigger('click')

    expect(createGame).toHaveBeenCalledWith({ id: 7, name: 'Rustaceans', is_default: false })
  })

  it('links to the custom pool editor', async () => {
    const wrapper = await mountHome()

    expect(wrapper.get('a[href="/pools/new"]').text()).toContain('custom pool')
  })

  it('reports a failed pool list while still allowing a default-pool game', async () => {
    vi.mocked(fetchPools).mockRejectedValue(new Error('unavailable'))
    vi.mocked(createGame).mockResolvedValue({ code: 'ABC123', host_token: 't' })
    const wrapper = await mountHome()

    expect(wrapper.get('[role="alert"]').text()).toContain('Could not load saved pools')
    await wrapper.get('button[data-test="create-game"]').trigger('click')
    await flushPromises()

    expect(createGame).toHaveBeenCalledWith(undefined)
    expect(wrapper.text()).toContain('ABC123')
  })

  it('reports a failed game creation', async () => {
    vi.mocked(createGame).mockRejectedValue(new Error('unavailable'))
    const wrapper = await mountHome()

    await wrapper.get('button[data-test="create-game"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Could not create a game')
  })
})
