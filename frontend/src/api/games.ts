import type { components } from './schema'

export type CreateGameResponse = components['schemas']['CreateGameResponse']

export async function createGame(): Promise<CreateGameResponse> {
  const response = await fetch('/games', { method: 'POST' })
  if (!response.ok) {
    throw new Error(`Create game failed with status ${response.status}`)
  }
  return (await response.json()) as CreateGameResponse
}
