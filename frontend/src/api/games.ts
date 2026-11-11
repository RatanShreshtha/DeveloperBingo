import type { components } from './schema'

export type HostLink = components['schemas']['HostLink']
export type DrawHistoryResponse = components['schemas']['DrawHistoryResponse']

export async function createGame(): Promise<HostLink> {
  const response = await fetch('/games', { method: 'POST' })
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
