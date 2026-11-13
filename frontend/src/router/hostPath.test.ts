import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { createRouter, hostPath } from '.'

describe('the host path', () => {
  it('is read back by the host route as the same code and token', async () => {
    const link = { code: 'AB/C 12', host_token: 'se&cret=token' }
    const router = createRouter(createMemoryHistory())

    await router.push(hostPath(link))

    const route = router.currentRoute.value
    const host = router.getRoutes().find((known) => known.path === '/host/:code')
    const props = (host?.props.default as (route: unknown) => unknown)(route)
    expect(props).toEqual({ code: link.code, token: link.host_token })
  })
})
