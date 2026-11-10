import type { JoinResult, PrizeBoard, TicketCells } from '../realtime/socket'
import { EARLY_FIVE } from '../prizes'

/**
 * A successful join, as the server acknowledges it. Tests use this so that adding a
 * field to the join result changes one place rather than every mock.
 */
export function joinedResult(
  ticket: TicketCells,
  ticks: string[] = [],
  prizes: PrizeBoard = { [EARLY_FIVE]: null },
): JoinResult {
  return { ok: true, ticket, ticks, prizes }
}
