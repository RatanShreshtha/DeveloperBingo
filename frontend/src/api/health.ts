import type { components } from './schema'

export type HealthResponse = components['schemas']['HealthResponse']

export async function fetchHealth(
  fetchImpl: typeof fetch = fetch,
): Promise<HealthResponse> {
  const response = await fetchImpl('/health')
  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}`)
  }
  return (await response.json()) as HealthResponse
}
