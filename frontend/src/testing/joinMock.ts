import type { JoinAck, PrizeBoardEntry } from '../realtime/socket'

/**
 * A successful join, as the server acknowledges it. Tests use this so that adding a
 * field to the join result changes one place rather than every mock.
 */
export function joinedResult(
  ticket: JoinAck['ticket'],
  ticks: string[] = [],
  prizes: PrizeBoardEntry[] = [{ prize: 'early_five', awarded_to: null }],
): JoinAck {
  return { ok: true, ticket, ticks, prizes }
}
