import type { components } from './schema'

export type HealthResponse = components['schemas']['HealthResponse']

export class HealthRequestError extends Error {
  readonly status: number

  constructor(status: number) {
    super(`Health request failed with status ${status}`)
    this.name = 'HealthRequestError'
    this.status = status
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/health')
  if (!response.ok) {
    throw new HealthRequestError(response.status)
  }
  return (await response.json()) as HealthResponse
}
