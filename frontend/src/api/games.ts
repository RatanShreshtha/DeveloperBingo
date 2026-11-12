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

export type GameHistoryResponse = components['schemas']['GameHistoryResponse']

/** The history request failed; `status` is the HTTP status (404: none stored, 503: store down). */
export class GameHistoryError extends Error {
  readonly status: number
  constructor(status: number) {
    super(`Game history request failed with status ${status}`)
    this.status = status
  }
}

export async function fetchGameHistory(code: string): Promise<GameHistoryResponse> {
  const response = await fetch(`/games/${encodeURIComponent(code)}/history`)
  if (!response.ok) {
    throw new GameHistoryError(response.status)
  }
  return (await response.json()) as GameHistoryResponse
}

export async function fetchDrawHistory(code: string): Promise<DrawHistoryResponse> {
  const response = await fetch(`/games/${encodeURIComponent(code)}/draws`)
  if (!response.ok) {
    throw new Error(`Draw history request failed with status ${response.status}`)
  }
  return (await response.json()) as DrawHistoryResponse
}
