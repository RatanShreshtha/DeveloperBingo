import type { HostSnapshot, PlayerSnapshot } from '../realtime/protocol'

const OPEN_BOARD: PlayerSnapshot['prizes'] = [{ prize: 'early_five', awarded_to: [] }]

/** A successful join as the server acknowledges it. Override only what a test is about. */
export function playerSnapshot(overrides: Partial<PlayerSnapshot> = {}): PlayerSnapshot {
  return {
    ok: true,
    status: 'lobby',
    end_reason: null,
    players: ['Ada'],
    draws: [],
    prizes: OPEN_BOARD,
    ticket: [['Algorithm', null, 'JSON']],
    ticks: [],
    pending_claims: [],
    rejoin_token: 'token-1',
    ...overrides,
  }
}

/** A successful watch as the server acknowledges it. */
export function hostSnapshot(overrides: Partial<HostSnapshot> = {}): HostSnapshot {
  return {
    ok: true,
    status: 'lobby',
    end_reason: null,
    players: [],
    draws: [],
    prizes: OPEN_BOARD,
    claims: [],
    pool: { columns: [] },
    pool_name: null,
    window_open: false,
    ...overrides,
  }
}
