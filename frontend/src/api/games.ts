import type { components } from './schema'

export type CreateGameResponse = components['schemas']['CreateGameResponse']

export async function createGame(): Promise<CreateGameResponse> {
  const response = await fetch('/games', { method: 'POST' })
  if (!response.ok) {
    throw new Error(`Create game failed with status ${response.status}`)
  }
  return (await response.json()) as CreateGameResponse
}

export async function startGame(code: string, hostToken: string): Promise<void> {
  const response = await fetch(`/games/${encodeURIComponent(code)}/start`, {
    method: 'POST',
    headers: { 'X-Host-Token': hostToken },
  })
  if (!response.ok) {
    throw new Error(`Start game failed with status ${response.status}`)
  }
}
