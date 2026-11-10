import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import HealthView from './HealthView.vue'

function stubHealthResponse(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
  )
}

async function renderHealthView() {
  const wrapper = mount(HealthView, {
    global: { plugins: [createPinia()] },
  })
  await flushPromises()
  return wrapper
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('HealthView', () => {
  it('shows the backend is up when the database is reachable', async () => {
    stubHealthResponse({ status: 'ok', database: 'up' })

    const wrapper = await renderHealthView()

    expect(wrapper.text()).toContain('Status: ok')
    expect(wrapper.text()).toContain('Database: up')
  })

  it('shows the backend is degraded when the database is down', async () => {
    stubHealthResponse({ status: 'degraded', database: 'down' })

    const wrapper = await renderHealthView()

    expect(wrapper.text()).toContain('Status: degraded')
    expect(wrapper.text()).toContain('Database: down')
  })

  it('shows a message when the backend cannot be reached', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )

    const wrapper = await renderHealthView()

    expect(wrapper.text()).toContain('Could not reach the backend')
  })
})
