import type { components } from './schema'
import { requestJson } from './request'

export type HostLink = components['schemas']['HostLink']

/** Create a game on the default pool, or on the saved pool with this id. */
export async function createGame(poolId?: number): Promise<HostLink> {
  return poolId === undefined
    ? requestJson<HostLink>('/games', { method: 'POST' })
    : requestJson<HostLink>('/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: poolId }),
      })
}

export type GameHistoryResponse = components['schemas']['GameHistoryResponse']

export async function fetchGameHistory(code: string): Promise<GameHistoryResponse> {
  return requestJson<GameHistoryResponse>(`/games/${encodeURIComponent(code)}/history`)
}
