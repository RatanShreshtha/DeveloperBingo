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
})

describe('HostView claims', () => {
  it('shows draws above prizes and claims in two columns', async () => {
    fake.answer('watch_lobby', hostSnapshot())

    const wrapper = mount(HostView, {
      props: { code: 'ABC123', token: 'secret-token' },
      global: { plugins: makePlugins() },
    })
    await flushPromises()

    const headings = wrapper.findAll('h2.card-title')
    expect(headings.slice(0, 3).map((heading) => heading.text())).toEqual(['Draws', 'Prizes', 'Claims'])
    expect(headings[0].element.closest('.grid')).toBeNull()
    expect(headings[1].element.closest('.grid')).toBe(headings[2].element.closest('.grid'))
    expect(headings[1].element.closest('.grid')?.classList.contains('md:grid-cols-2')).toBe(true)
  })

  it('lists every claim with who made it, the prize, and whether it was accepted or why not', async () => {
    fake.answer(
      'watch_lobby',
      hostSnapshot({
        players: ['Ada', 'Grace'],
        prizes: [],
        claims: [
          { player: 'Ada', prize: 'early_five', accepted: false, error: 'claim_not_valid' },
          { player: 'Grace', prize: 'top_line', accepted: true, error: null },
        ],
      }),
    )

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
