import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchDefaultPool, PoolRefusedError, savePool } from '../../api/pools'
import { makePlugins } from '../../testing/testRouter'
import PoolEditorView from '../PoolEditorPage.vue'

vi.mock('../../api/pools', async () => (await import('../../testing/apiMock')).apiPoolsMock())

const SIZES = [9, 10, 10, 10, 10, 10, 10, 10, 11]

function defaultColumns() {
  let n = 0
  return SIZES.map((size) =>
    Array.from({ length: size }, () => {
      n += 1
      return { name: `Topic ${n}`, explanation: `Topic ${n} explained` }
    }),
  )
}

beforeEach(() => {
  vi.mocked(fetchDefaultPool).mockReset()
  vi.mocked(fetchDefaultPool).mockResolvedValue({ columns: defaultColumns() })
  vi.mocked(savePool).mockReset()
})

async function mountEditor() {
  const wrapper = mount(PoolEditorView, { global: { plugins: makePlugins() } })
  await flushPromises()
  return wrapper
}

describe('PoolEditorView', () => {
  it('starts as a copy of the default pool: 90 rows, each a name and an explanation', async () => {
    const wrapper = await mountEditor()

    const names = wrapper.findAll('input[data-test="topic-name"]')
    const explanations = wrapper.findAll('input[data-test="topic-explanation"]')
    expect(names).toHaveLength(90)
    expect(explanations).toHaveLength(90)
    expect((names[0].element as HTMLInputElement).value).toBe('Topic 1')
    expect((explanations[89].element as HTMLInputElement).value).toBe('Topic 90 explained')
    expect(names[0].attributes('aria-label')).toBe('Topic 1 name')
    expect(explanations[89].attributes('aria-label')).toBe('Topic 90 explanation')
  })

  it('saves the edited pool under its name, topics in list order', async () => {
    vi.mocked(savePool).mockResolvedValue({ id: 2, name: 'Mine', is_default: false })
    const wrapper = await mountEditor()

    await wrapper.get('input[data-test="pool-name"]').setValue('Mine')
    await wrapper.findAll('input[data-test="topic-name"]')[1].setValue('Edited')
    await wrapper.get('button[data-test="save-pool"]').trigger('click')
    await flushPromises()

    const [name, topics] = vi.mocked(savePool).mock.calls[0]
    expect(name).toBe('Mine')
    expect(topics).toHaveLength(90)
    expect(topics[0]).toEqual({ name: 'Topic 1', explanation: 'Topic 1 explained' })
    expect(topics[1]).toEqual({ name: 'Edited', explanation: 'Topic 2 explained' })
    expect(wrapper.text()).toContain('Saved')
  })

  it('shows the rule that broke when the pool is refused', async () => {
    vi.mocked(savePool).mockRejectedValue(
      new PoolRefusedError('duplicate_topic', "topic 'Topic 1' appears more than once"),
    )
    const wrapper = await mountEditor()

    await wrapper.get('input[data-test="pool-name"]').setValue('Mine')
    await wrapper.get('button[data-test="save-pool"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain("topic 'Topic 1' appears more than once")
    expect(wrapper.text()).not.toContain('Saved')
  })

  it('says so when the default pool cannot be loaded', async () => {
    vi.mocked(fetchDefaultPool).mockRejectedValue(new Error('down'))
    const wrapper = await mountEditor()

    expect(wrapper.get('[role="alert"]').text()).toContain('Could not load')
    expect(wrapper.find('button[data-test="save-pool"]').exists()).toBe(false)
  })

  it('reports other save failures and clears the error after a successful retry', async () => {
    vi.mocked(savePool).mockRejectedValueOnce(new Error('unavailable'))
    vi.mocked(savePool).mockResolvedValueOnce({ id: 2, name: 'Mine', is_default: false })
    const wrapper = await mountEditor()

    await wrapper.get('button[data-test="save-pool"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Could not save the pool')

    await wrapper.get('button[data-test="save-pool"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Saved')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })
})
