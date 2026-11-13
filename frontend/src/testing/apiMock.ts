import { vi } from 'vitest'

/** The HTTP functions of the games API, as mocks. */
export function apiGamesMock() {
  return {
    createGame: vi.fn(),
    fetchGameHistory: vi.fn(),
  }
}

/** The HTTP functions of the pools API, as mocks. By default only the default pool is saved. The
 * refusal error is the real class, so what the tests check is what the components check. */
export async function apiPoolsMock() {
  const { PoolRefusedError } = await vi.importActual<typeof import('../api/pools')>('../api/pools')
  return {
    PoolRefusedError,
    fetchDefaultPool: vi.fn(async () => ({ columns: [] })),
    fetchPools: vi.fn(async () => [{ id: 1, name: 'Default', is_default: true }]),
    savePool: vi.fn(),
  }
}
