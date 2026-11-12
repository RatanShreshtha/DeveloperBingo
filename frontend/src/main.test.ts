import { flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { createApplication } from './main'
import { useTransport } from './realtime/transport'
import { installFakeTransport } from './testing/fakeTransport'
import { hostSnapshot } from './testing/snapshots'

let dispose: (() => void) | undefined

afterEach(() => {
  dispose?.()
  dispose = undefined
  sessionStorage.clear()
  useTransport(null)
  vi.unstubAllGlobals()
})

describe('application routes', () => {
  it('mounts the app and navigates to every lazy page with its route props', async () => {
    sessionStorage.clear()
    const fake = installFakeTransport()
    fake.answer('watch_lobby', hostSnapshot())
    const fetch = vi.fn(async (url: string) => {
      if (url === '/health') {
        return new Response(JSON.stringify({ status: 'ok', database: 'up' }))
      }
      if (url === '/pools') {
        return new Response(JSON.stringify([{ id: 1, name: 'Default', is_default: true }]))
      }
      if (url === '/pools/default') {
        return new Response(JSON.stringify({ columns: [[{ name: 'Cache', explanation: 'A store' }]] }))
      }
      if (url === '/games/ABC123/history') {
        return new Response(JSON.stringify({
          code: 'ABC123', reason: 'host', pool_name: null, draws: [], claims: [], winners: [],
        }))
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetch)

    const { app, router } = createApplication(createMemoryHistory())
    const element = document.createElement('div')
    document.body.appendChild(element)
    dispose = () => {
      app.unmount()
      element.remove()
    }

    await router.push('/')
    await router.isReady()
    app.mount(element)
    await flushPromises()
    expect(element.textContent).toContain('Play DeveloperBingo')
    expect(element.textContent).toContain('Database: up')

    await router.push('/join')
    await flushPromises()
    expect(element.querySelector('input[name="code"]')).not.toBeNull()

    await router.push('/pools/new')
    await flushPromises()
    expect(element.textContent).toContain('New custom pool')
    expect(element.querySelector('input[data-test="topic-name"]')).not.toBeNull()

    await router.push('/host/ABC123?token=host-token')
    await flushPromises()
    expect(element.textContent).toContain('Host dashboard')
    expect(fake.payloads('watch_lobby')).toEqual([{ code: 'ABC123', host_token: 'host-token' }])

    await router.push('/games/ABC123')
    await flushPromises()
    expect(element.textContent).toContain('Your game')
    expect(element.querySelector('[data-test="join-link"]')).not.toBeNull()

    await router.push('/games/ABC123/history')
    await flushPromises()
    expect(element.textContent).toContain('Game ABC123')
    expect(element.textContent).toContain('The host ended the game.')
    expect(fetch).toHaveBeenCalledWith('/games/ABC123/history', undefined)
  })
})
