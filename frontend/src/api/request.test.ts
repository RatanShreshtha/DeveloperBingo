import { afterEach, describe, expect, it, vi } from 'vitest'
import { createGame, fetchGameHistory } from './games'
import { fetchHealth } from './health'
import { PoolRefusedError, savePool } from './pools'
import { HttpError, NotFoundError, UnavailableError } from './request'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('HTTP requests', () => {
  it('sends the selected pool when creating a game', async () => {
    const fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ code: 'ABC123', host_token: 't' })),
    )
    vi.stubGlobal('fetch', fetch)

    await expect(createGame({ id: 7, is_default: false })).resolves.toEqual({
      code: 'ABC123',
      host_token: 't',
    })
    expect(fetch).toHaveBeenCalledWith('/games', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pool_id: 7 }),
    })
  })

  it('creates a default-pool game without a request body', async () => {
    const fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ code: 'ABC123', host_token: 't' })),
    )
    vi.stubGlobal('fetch', fetch)

    await createGame()

    expect(fetch).toHaveBeenCalledWith('/games', { method: 'POST' })
  })

  it('creates a game on the default pool without sending its id', async () => {
    const fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ code: 'ABC123', host_token: 't' })),
    )
    vi.stubGlobal('fetch', fetch)

    await createGame({ id: 1, is_default: true })

    expect(fetch).toHaveBeenCalledWith('/games', { method: 'POST' })
  })

  it('encodes the history code', async () => {
    const fetch = vi.fn(async () => new Response(JSON.stringify({})))
    vi.stubGlobal('fetch', fetch)

    await fetchGameHistory('A/B')

    expect(fetch).toHaveBeenCalledWith('/games/A%2FB/history', undefined)
  })

  it.each([
    [404, NotFoundError],
    [503, UnavailableError],
  ])(
    'types a %i response, which is still an HttpError with its status',
    async (status, failure) => {
      vi.stubGlobal(
        'fetch',
        vi.fn(async () => new Response(null, { status })),
      )

      const result = fetchGameHistory('ABC123')

      await expect(result).rejects.toBeInstanceOf(failure)
      await expect(result).rejects.toBeInstanceOf(HttpError)
      await expect(result).rejects.toMatchObject({ status })
    },
  )

  it('leaves any other failing status as a plain HttpError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(null, { status: 500 })),
    )

    const result = fetchGameHistory('ABC123')

    await expect(result).rejects.toBeInstanceOf(HttpError)
    await expect(result).rejects.not.toBeInstanceOf(NotFoundError)
    await expect(result).rejects.not.toBeInstanceOf(UnavailableError)
  })

  it('preserves the pool refusal details from a 422 response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              detail: {
                rule: 'duplicate_topic',
                message: 'Topic appears twice',
              },
            }),
            { status: 422 },
          ),
      ),
    )

    const result = savePool('Mine', [{ name: 'Topic', explanation: 'A topic' }])

    await expect(result).rejects.toBeInstanceOf(PoolRefusedError)
    await expect(result).rejects.toMatchObject({
      rule: 'duplicate_topic',
      message: 'Topic appears twice',
    })
  })

  it('preserves other pool HTTP failures rather than treating them as refusals', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(null, { status: 503 })),
    )

    await expect(savePool('Mine', [])).rejects.toMatchObject({ status: 503 })
    await expect(savePool('Mine', [])).rejects.toBeInstanceOf(HttpError)
  })

  it('propagates a network failure', async () => {
    const failure = new TypeError('network unavailable')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(failure))

    await expect(fetchHealth()).rejects.toBe(failure)
  })
})
