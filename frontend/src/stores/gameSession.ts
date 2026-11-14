import { computed, ref } from 'vue'
import { messageFor, UNREACHABLE } from '../utils/errors'
import type {
  DrawnTopic,
  GameEnd,
  GameSnapshot,
  PrizeBoardEntry,
  Refusal,
} from '../realtime/protocol'
import { transport } from '../realtime/transport'

type Refusable = { ok: true } | Refusal

// A role this tab holds in the game: 'player' once it has joined as a player, 'host' once it
// watches as host. Reconnect restores each role the tab holds.
export type Role = 'player' | 'host'

export function createGameSession() {
  const net = transport()
  const status = ref<GameSnapshot['status']>('lobby')
  const endReason = ref<GameEnd['reason'] | null>(null)
  const started = computed(() => status.value !== 'lobby')
  const ended = computed(() => status.value === 'ended')
  const players = ref<string[]>([])
  const draws = ref<DrawnTopic[]>([])
  const drawnNames = computed(() => draws.value.map((draw) => draw.name))
  const prizes = ref<PrizeBoardEntry[]>([])
  const error = ref<string | null>(null)
  const actionError = ref<string | null>(null)
  const roles = new Set<Role>()

  function recordEnd(reason: GameEnd['reason']) {
    status.value = 'ended'
    endReason.value = reason
  }

  // The host receives its own draw both in the acknowledgement and the room broadcast.
  function recordDraw(draw: DrawnTopic) {
    if (!draws.value.some((known) => known.position === draw.position)) {
      draws.value.push(draw)
    }
  }

  function applySnapshot(snapshot: GameSnapshot) {
    status.value = snapshot.status
    endReason.value = snapshot.end_reason
    players.value = snapshot.players
    draws.value = snapshot.draws
    prizes.value = snapshot.prizes
  }

  /**
   * Sends one action and says why it failed. Null means it did not happen: the server refused it,
   * or could not be reached, and `actionError` holds the message either way.
   */
  async function attempt<T extends Refusable>(
    call: () => Promise<T>,
  ): Promise<T | null> {
    actionError.value = null
    let result: T
    try {
      result = await call()
    } catch {
      actionError.value = UNREACHABLE
      return null
    }
    if (!result.ok) {
      actionError.value = messageFor(result.error)
      return null
    }
    return result
  }

  net.listen('lobby_updated', (event) => {
    players.value = event.players
  })
  net.listen('game_started', () => {
    if (status.value === 'lobby') {
      status.value = 'started'
    }
  })
  net.listen('topic_drawn', recordDraw)
  net.listen('prize_awarded', (award) => {
    prizes.value = prizes.value.map((entry) =>
      entry.prize === award.prize
        ? { ...entry, awarded_to: award.awarded_to }
        : entry,
    )
  })

  return {
    net,
    status,
    endReason,
    started,
    ended,
    players,
    draws,
    drawnNames,
    prizes,
    error,
    actionError,
    roles,
    recordEnd,
    recordDraw,
    applySnapshot,
    attempt,
  }
}

export type GameSession = ReturnType<typeof createGameSession>
