import { vi } from 'vitest'

/**
 * Every function the socket module exports, as mocks. Test files pull this in
 * through vi.mock, so they all mock the same surface and none drifts behind.
 */
export function socketModuleMock() {
  return {
    joinGame: vi.fn(),
    watchLobby: vi.fn(),
    onLobbyUpdated: vi.fn(),
    startGame: vi.fn(),
    drawTopic: vi.fn(),
    onGameStarted: vi.fn(),
    onTopicDrawn: vi.fn(),
  }
}
