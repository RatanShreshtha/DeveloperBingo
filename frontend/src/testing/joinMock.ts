import type { JoinResult, PrizeBoard, TicketCells } from '../realtime/socket'

/**
 * A successful join, as the server acknowledges it. Tests use this so that adding a
 * field to the join result changes one place rather than every mock.
 */
export function joinedResult(
  ticket: TicketCells,
  ticks: string[] = [],
  prizes: PrizeBoard = { early_five: null },
): JoinResult {
  return { ok: true, ticket, ticks, prizes }
}
