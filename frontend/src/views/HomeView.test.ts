import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createGame } from '../api/games'
import { fetchPools } from '../api/pools'
import { makePlugins } from './testRouter'
import HomeView from './HomeView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../api/pools', async () => (await import('../testing/apiMock')).apiPoolsMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  vi.mocked(createGame).mockReset()
  vi.mocked(fetchPools).mockClear()
})

async function mountHome() {
  const wrapper = mount(HomeView, { global: { plugins: makePlugins() } })
  await flushPromises()
  return wrapper
}

describe('HomeView', () => {
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

    expect(createGame).toHaveBeenCalledWith(undefined)
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

    expect(createGame).toHaveBeenCalledWith(7)
  })

  it('links to the custom pool editor', async () => {
    const wrapper = await mountHome()

    expect(wrapper.get('a[href="/pools/new"]').text()).toContain('custom pool')
  })
})
