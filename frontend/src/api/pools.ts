import type { components } from './schema'

export type PoolResponse = components['schemas']['PoolResponse']
export type TopicResponse = components['schemas']['TopicResponse']
export type GamePoolResponse = components['schemas']['GamePoolResponse']
export type PoolSummary = components['schemas']['PoolSummaryResponse']

/** A pool the library refused to save: `rule` names the pool rule that broke. */
export class PoolRefusedError extends Error {
  rule: string
  constructor(rule: string, message: string) {
    super(message)
    this.rule = rule
  }
}

export async function fetchDefaultPool(): Promise<PoolResponse> {
  const response = await fetch('/pools/default')
  if (!response.ok) {
    throw new Error(`Default pool request failed with status ${response.status}`)
  }
  return (await response.json()) as PoolResponse
}

export async function fetchGamePool(code: string): Promise<GamePoolResponse> {
  const response = await fetch(`/games/${encodeURIComponent(code)}/pool`)
  if (!response.ok) {
    throw new Error(`Game pool request failed with status ${response.status}`)
  }
  return (await response.json()) as GamePoolResponse
}

export async function fetchPools(): Promise<PoolSummary[]> {
  const response = await fetch('/pools')
  if (!response.ok) {
    throw new Error(`Pool list request failed with status ${response.status}`)
  }
  return (await response.json()) as PoolSummary[]
}

export async function savePool(name: string, topics: TopicResponse[]): Promise<PoolSummary> {
  const response = await fetch('/pools', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, topics }),
  })
  if (response.status === 422) {
    const body = (await response.json()) as components['schemas']['PoolRefused']
    throw new PoolRefusedError(body.detail.rule, body.detail.message)
  }
  if (!response.ok) {
    throw new Error(`Saving the pool failed with status ${response.status}`)
  }
  return (await response.json()) as PoolSummary
}
