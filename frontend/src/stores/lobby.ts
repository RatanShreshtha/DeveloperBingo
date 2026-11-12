import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { createGame, fetchDrawHistory } from '../api/games'
import type { Prize } from '../prizes'
import {
  claimPrize as sendClaim,
  drawTopic,
  endGame,
  joinGame,
  onClaimLogged,
  onGameEnded,
  onGameStarted,
  onLobbyUpdated,
  onPrizeAwarded,
  onReconnect,
  onTopicDrawn,
  startGame,
  tickTopic,
  untickTopic,
  watchLobby,
  type DrawnTopic,
  type ClaimLogEntry,
  type ErrorCode,
  type GameEnd,
  type HostLink,
  type JoinAck,
  type PlayerRef,
  type PrizeBoardEntry,
  type Refusal,
} from '../realtime/socket'

// Every error code needs a message: a missing one is a type error.
const ERROR_MESSAGES: Record<ErrorCode, string> = {
  name_taken: 'That name is already taken in this game',
  already_joined: 'You have already joined a game from this window',
  game_full: 'This game is full',
  already_started: 'This game has already started',
  game_ended: 'The game has ended',
  not_found: 'No game found with that code',
  not_host: 'This host link is not valid for this game',
  not_started: 'The game has not started yet',
  no_topics_left: 'Every topic has already been drawn',
  not_drawn: 'That topic has not been drawn yet',
  not_on_ticket: 'That topic is not on your ticket',
  not_a_player: 'You are not in this game',
  not_joined: 'You have not joined this game from this window',
  claim_not_valid: 'This claim does not complete the prize yet',
  prize_taken: 'Someone has already been awarded this prize',
  unknown_prize: 'That prize does not exist',
  settlement_open: 'A claim is being settled. Draws resume in a moment.',
  claim_pending: 'Your claim is waiting to be settled, so you cannot untick a topic now',
  invalid_message: 'That request was not understood. Please reload the page.',
}

export function messageFor(code: ErrorCode): string {
  return ERROR_MESSAGES[code]
}

type Refusable = { ok: true } | Refusal

export const useLobbyStore = defineStore('lobby', () => {
  const players = ref<string[]>([])
  const ticket = ref<JoinAck['ticket'] | null>(null)
  const started = ref(false)
  // Why the game is over: someone claimed the full house, or the host ended it. Null while it runs.
  const endReason = ref<GameEnd['reason'] | null>(null)
  const ended = computed(() => endReason.value !== null)
  const draws = ref<DrawnTopic[]>([])
  // This player's own identity in the game, and the topics they have ticked.
  const player = ref<PlayerRef | null>(null)
  const ticks = ref<string[]>([])
  const drawnNames = computed(() => draws.value.map((draw) => draw.name))
  // Each prize in the order the server lists them, and who it was awarded to.
  const prizes = ref<PrizeBoardEntry[]>([])
  // Prizes this player has claimed whose settlement window has not closed yet.
  const pendingClaims = ref<Prize[]>([])
  const isPending = (prize: Prize) => pendingClaims.value.includes(prize)
  const isAwarded = (prize: Prize) =>
    prizes.value.some((entry) => entry.prize === prize && entry.awarded_to.length > 0)
  // Every claim in the game, accepted or refused, in order. Only the host is told these.
  const claims = ref<ClaimLogEntry[]>([])
  // Problems loading the lobby, shown in place of it.
  const error = ref<string | null>(null)
  // Refusals of something the player or host did, shown next to the controls.
  const actionError = ref<string | null>(null)

  onLobbyUpdated((names) => {
    players.value = names
  })
  onGameStarted(() => {
    started.value = true
  })
  onGameEnded((end) => {
    recordEnd(end.reason)
  })
  onClaimLogged((claim) => {
    claims.value.push(claim)
  })
  onTopicDrawn(recordDraw)
  onReconnect(rejoin)
  onPrizeAwarded((award) => {
    prizes.value = prizes.value.map((entry) =>
      entry.prize === award.prize ? { ...entry, awarded_to: award.awarded_to } : entry,
    )
  })

  function recordEnd(reason: GameEnd['reason']) {
    endReason.value = reason
  }

  // Draws come both from our own ack and from the room broadcast, which
  // reaches the host too. Positions are unique per game, so keep the first.
  function recordDraw(draw: DrawnTopic) {
    if (!draws.value.some((known) => known.position === draw.position)) {
      draws.value.push(draw)
    }
  }

  // Runs a host action, returning its result, or null after showing why it was refused.
  async function attempt<T extends Refusable>(call: () => Promise<T>): Promise<T | null> {
    actionError.value = null
    const result = await call()
    if (!result.ok) {
      actionError.value = messageFor((result as Refusal).error)
      return null
    }
    return result
  }

  async function create(poolId?: number) {
    return createGame(poolId)
  }

  async function join(code: string, name: string): Promise<boolean> {
    error.value = null
    ticket.value = null
    const result = await joinGame(code, name)
    if (!result.ok) {
      error.value = messageFor(result.error)
      return false
    }
    player.value = { code, name }
    restore(result)
    return true
  }

  // A dropped socket is a new socket to the server, which acts only for players who
  // joined on it. Joining again by the same name gets the player their place back.
  async function rejoin() {
    const who = player.value
    if (!who) {
      return
    }
    const result = await joinGame(who.code, who.name)
    if (!result.ok) {
      actionError.value = messageFor(result.error)
      return
    }
    restore(result)
  }

  // Takes what the server holds for this player: their ticket, ticks and the prize board.
  function restore(result: JoinAck) {
    ticket.value = result.ticket
    ticks.value = result.ticks
    prizes.value = result.prizes
  }

  // Claims a prize. The server answers once the prize's settlement window closes, so the claim
  // is pending until then. Winners are announced to the room, which updates the board.
  async function claimPrize(prize: Prize) {
    if (!player.value || isPending(prize)) {
      return
    }
    pendingClaims.value = [...pendingClaims.value, prize]
    try {
      await attempt(() => sendClaim(prize))
    } finally {
      pendingClaims.value = pendingClaims.value.filter((known) => known !== prize)
    }
  }

  // Ticks the topic if it isn't ticked, otherwise unticks it. The list changes only
  // once the server agrees.
  async function toggleTick(topic: string) {
    if (!player.value) {
      return
    }
    const isTicked = ticks.value.includes(topic)
    const send = isTicked ? untickTopic : tickTopic
    const result = await attempt(() => send(topic))
    if (!result?.ok) {
      return
    }
    ticks.value = isTicked
      ? ticks.value.filter((known) => known !== topic)
      : [...ticks.value, topic]
  }

  async function watchAsHost(link: HostLink) {
    error.value = null
    const result = await watchLobby(link)
    if (result.ok) {
      players.value = result.players
      prizes.value = result.prizes
      claims.value = result.claims
    } else {
      error.value = messageFor(result.error)
    }
  }

  async function loadDrawHistory(code: string) {
    try {
      const history = await fetchDrawHistory(code)
      draws.value = [...history.draws]
      if (history.draws.length > 0) {
        started.value = true
      }
    } catch {
      error.value = 'Could not load the draw history'
    }
  }

  async function start(link: HostLink) {
    if (await attempt(() => startGame(link))) {
      started.value = true
    }
  }

  async function end(link: HostLink) {
    if (await attempt(() => endGame(link))) {
      recordEnd('host')
    }
  }

  async function drawNext(link: HostLink) {
    const result = await attempt(() => drawTopic(link))
    if (result?.ok) {
      recordDraw(result.draw)
    }
  }

  return {
    players,
    ticket,
    started,
    ended,
    endReason,
    draws,
    drawnNames,
    player,
    ticks,
    prizes,
    isAwarded,
    isPending,
    claims,
    messageFor,
    error,
    actionError,
    create,
    join,
    toggleTick,
    claimPrize,
    watchAsHost,
    loadDrawHistory,
    start,
    end,
    drawNext,
  }
})
