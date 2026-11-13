import type { components } from './schema'
import type { PoolSummary } from './pools'
import { requestJson } from './request'

export type HostLink = components['schemas']['HostLink']

/** Create a game on this pool. The default pool is the server's fallback, so it and no pool at all
 * send no pool id. */
export async function createGame(pool?: Pick<PoolSummary, 'id' | 'is_default'>): Promise<HostLink> {
  return pool === undefined || pool.is_default
    ? requestJson<HostLink>('/games', { method: 'POST' })
    : requestJson<HostLink>('/games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: pool.id }),
      })
}

export type GameHistoryResponse = components['schemas']['GameHistoryResponse']

export async function fetchGameHistory(code: string): Promise<GameHistoryResponse> {
  return requestJson<GameHistoryResponse>(`/games/${encodeURIComponent(code)}/history`)
}
