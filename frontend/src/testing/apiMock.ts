import { vi } from 'vitest'

/**
 * The HTTP functions of the games API, as mocks. The history defaults to an
 * empty game, so views that load it on mount behave like a fresh lobby.
 */
export function apiGamesMock() {
  return {
    createGame: vi.fn(),
    fetchDrawHistory: vi.fn(async () => ({ draws: [] })),
  }
}
