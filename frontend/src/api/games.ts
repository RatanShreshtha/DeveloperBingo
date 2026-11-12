import type { components } from './schema'

export type HostLink = components['schemas']['HostLink']
export type DrawHistoryResponse = components['schemas']['DrawHistoryResponse']

/** Create a game on the default pool, or on the saved pool with this id. */
export async function createGame(poolId?: number): Promise<HostLink> {
  const response =
    poolId === undefined
      ? await fetch('/games', { method: 'POST' })
      : await fetch('/games', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pool_id: poolId }),
        })
  if (!response.ok) {
    throw new Error(`Create game failed with status ${response.status}`)
  }
  return (await response.json()) as HostLink
}

export async function fetchDrawHistory(code: string): Promise<DrawHistoryResponse> {
  const response = await fetch(`/games/${encodeURIComponent(code)}/draws`)
  if (!response.ok) {
    throw new Error(`Draw history request failed with status ${response.status}`)
  }
  return (await response.json()) as DrawHistoryResponse
}
