import type { JoinResult, TicketCells } from '../realtime/socket'

/**
 * A successful join, as the server acknowledges it. Tests use this so that adding a
 * field to the join result changes one place rather than every mock.
 */
export function joinedResult(ticket: TicketCells, ticks: string[] = []): JoinResult {
  return { ok: true, ticket, ticks }
}
