import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { watchLobby } from '../realtime/socket'
import { makePlugins } from './testRouter'
import HostView from './HostView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../api/pools', () => ({ fetchDefaultPool: vi.fn(async () => ({ columns: [] })) }))
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  vi.mocked(watchLobby).mockReset()
})

describe('HostView claims', () => {
  it('lists every claim with who made it, the prize, and whether it was accepted or why not', async () => {
    vi.mocked(watchLobby).mockResolvedValue({
      ok: true,
      players: ['Ada', 'Grace'],
      prizes: [],
      claims: [
        { player: 'Ada', prize: 'early_five', accepted: false, error: 'claim_not_valid' },
        { player: 'Grace', prize: 'top_line', accepted: true, error: null },
      ],
    })

    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 'secret-token' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()

    const items = wrapper.findAll('[data-test="claim"]').map((item) => item.text())
    expect(items).toEqual([
      'Ada claimed Early five: refused. This claim does not complete the prize yet',
      'Grace claimed Top line: accepted',
    ])
  })
})
