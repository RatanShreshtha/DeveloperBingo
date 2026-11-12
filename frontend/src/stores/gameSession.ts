import { computed, ref } from 'vue'
import { messageFor } from '../utils/errors'
import type {
  DrawnTopic,
  GameEnd,
  GameSnapshot,
  PrizeBoardEntry,
  Refusal,
} from '../realtime/protocol'
import { transport } from '../realtime/transport'

type Refusable = { ok: true } | Refusal

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

  async function attempt<T extends Refusable>(call: () => Promise<T>): Promise<T | null> {
    actionError.value = null
    const result = await call()
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
      entry.prize === award.prize ? { ...entry, awarded_to: award.awarded_to } : entry,
    )
  })

  return {
    net, status, endReason, started, ended, players, draws, drawnNames, prizes,
    error, actionError, recordEnd, recordDraw, applySnapshot, attempt,
  }
}

export type GameSession = ReturnType<typeof createGameSession>
