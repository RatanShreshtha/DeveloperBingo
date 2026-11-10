import type { components } from './schema'

export type PoolResponse = components['schemas']['PoolResponse']
export type TopicResponse = components['schemas']['TopicResponse']

export async function fetchDefaultPool(): Promise<PoolResponse> {
  const response = await fetch('/pools/default')
  if (!response.ok) {
    throw new Error(`Default pool request failed with status ${response.status}`)
  }
  return (await response.json()) as PoolResponse
}
