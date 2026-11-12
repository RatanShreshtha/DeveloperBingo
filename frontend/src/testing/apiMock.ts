import { vi } from 'vitest'

/** The HTTP functions of the games API, as mocks. */
export function apiGamesMock() {
  return {
    createGame: vi.fn(),
    fetchGameHistory: vi.fn(),
  }
}

/** The HTTP functions of the pools API, as mocks. By default only the default pool is saved. */
export function apiPoolsMock() {
  return {
    PoolRefusedError: class PoolRefusedError extends Error {
      rule: string
      constructor(rule: string, message: string) {
        super(message)
        this.rule = rule
      }
    },
    fetchDefaultPool: vi.fn(async () => ({ columns: [] })),
    fetchGamePool: vi.fn(async () => ({ columns: [] })),
    fetchPools: vi.fn(async () => [{ id: 1, name: 'Default', is_default: true }]),
    savePool: vi.fn(),
  }
}
