import type { components } from './schema'
import { HttpError, requestJson } from './request'

export type PoolResponse = components['schemas']['PoolResponse']
export type TopicResponse = components['schemas']['TopicResponse']
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
  return requestJson<PoolResponse>('/pools/default')
}

export async function fetchPools(): Promise<PoolSummary[]> {
  return requestJson<PoolSummary[]>('/pools')
}

export async function savePool(name: string, topics: TopicResponse[]): Promise<PoolSummary> {
  try {
    return await requestJson<PoolSummary>('/pools', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, topics }),
    })
  } catch (error) {
    if (error instanceof HttpError && error.status === 422) {
      const body = (await error.response.json()) as components['schemas']['PoolRefused']
      throw new PoolRefusedError(body.detail.rule, body.detail.message)
    }
    throw error
  }
}
