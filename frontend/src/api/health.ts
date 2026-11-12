import type { components } from './schema'
import { requestJson } from './request'

export type HealthResponse = components['schemas']['HealthResponse']

export async function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/health')
}
