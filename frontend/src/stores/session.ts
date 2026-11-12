import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { createGame } from '../api/games'
import type { Prize } from '../prizes'
import type {
  ClaimLogEntry,
  ClaimSettled,
  DrawnTopic,
  ErrorCode,
  GameEnd,
  GameSnapshot,
  HostLink,
  PlayerRef,
  HostSnapshot,
  PlayerSnapshot,
  PrizeBoardEntry,
  Refusal,
} from '../realtime/protocol'
import { forgetSession, saveSession, savedSessionFor } from '../realtime/savedSession'
import { transport } from '../realtime/transport'

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

const UNREACHABLE = 'Could not reach the server. Check your connection and try again.'

export function messageFor(code: ErrorCode): string {
  return ERROR_MESSAGES[code]
}

type Refusable = { ok: true } | Refusal

// How a join started: from the join form, by reloading the page, or when the connection came back.
type JoinStart = 'fresh' | 'reload' | 'reconnect'
// What a failed join does: leave the game, show why in place of it, or show it beside the controls.
type JoinFailure = 'leave' | 'error' | 'actionError'

// A refused reload or reconnect means this player is no longer in the game (it may be gone after
// a server restart). An unreachable server says nothing about the game, so a reconnect keeps the
// player for the next try, and a reload keeps the saved session.
const JOIN_FAILURES: Record<JoinStart, { refused: JoinFailure; unreachable: JoinFailure }> = {
  fresh: { refused: 'error', unreachable: 'error' },
  reload: { refused: 'leave', unreachable: 'error' },
  reconnect: { refused: 'leave', unreachable: 'actionError' },
}
type HostSnapshotPool = HostSnapshot['pool']['columns']

export const useSessionStore = defineStore('session', () => {
  const net = transport()

  // --- The game, as everyone in it sees it ---
  const status = ref<GameSnapshot['status']>('lobby')
  // Why the game is over: someone claimed the full house, or the host ended it. Null while it runs.
  const endReason = ref<GameEnd['reason'] | null>(null)
  const started = computed(() => status.value !== 'lobby')
  const ended = computed(() => status.value === 'ended')
  const players = ref<string[]>([])
  const draws = ref<DrawnTopic[]>([])
  const drawnNames = computed(() => draws.value.map((draw) => draw.name))
  // Each prize in the order the server lists them, and who it was awarded to.
  const prizes = ref<PrizeBoardEntry[]>([])
  const isAwarded = (prize: Prize) =>
    prizes.value.some((entry) => entry.prize === prize && entry.awarded_to.length > 0)

  // Problems loading the game, shown in place of it.
  const error = ref<string | null>(null)
  // Refusals of something the player or host did, shown next to the controls.
  const actionError = ref<string | null>(null)

  // --- The player: their place in the game, ticket, ticks and claims ---
  const player = ref<PlayerRef | null>(null)
  const ticket = ref<PlayerSnapshot['ticket'] | null>(null)
  const ticks = ref<string[]>([])
  // Kept private. The server issues a new one with every join, and it lets a reload take the name back.
  let rejoinToken = ''
  // True once another window took this player over.
  const replaced = ref(false)
  // Prizes this player has claimed whose settlement window has not closed yet.
  const pendingClaims = ref<Prize[]>([])
  const isPending = (prize: Prize) => pendingClaims.value.includes(prize)

  // --- The host: their link to the game, and what only they see ---
  const hostLink = ref<HostLink | null>(null)
  // Every claim in the game, accepted or refused, in order. Only the host is told these.
  const claims = ref<ClaimLogEntry[]>([])
  const pool = ref<HostSnapshotPool | null>(null)
  const poolName = ref<string | null>(null)
  // True while a settlement window is open, which is why the server refuses draws.
  const windowOpen = ref(false)

  net.listen('lobby_updated', (event) => {
    players.value = event.players
  })
  net.listen('game_started', () => {
    if (status.value === 'lobby') {
      status.value = 'started'
    }
  })
  net.listen('game_ended', (end) => recordEnd(end.reason))
  net.listen('topic_drawn', recordDraw)
  net.listen('prize_awarded', (award) => {
    prizes.value = prizes.value.map((entry) =>
      entry.prize === award.prize ? { ...entry, awarded_to: award.awarded_to } : entry,
    )
  })
  net.listen('claim_logged', (claim) => {
    claims.value.push(claim)
  })
  net.listen('window_changed', (change) => {
    windowOpen.value = change.open
  })
  net.listen('claim_settled', settleClaim)
  net.listen('replaced', () => leave({ replaced: true }))
  net.onReconnect(recover)

  // A claim's window has closed. A win shows on the prize board, which the room is told of;
  // a refusal is shown to the player here.
  function settleClaim(claim: ClaimSettled) {
    pendingClaims.value = pendingClaims.value.filter((known) => known !== claim.prize)
    if (!claim.accepted && claim.error) {
      actionError.value = messageFor(claim.error)
    }
  }

  function recordEnd(reason: GameEnd['reason']) {
    status.value = 'ended'
    endReason.value = reason
    windowOpen.value = false
  }

  // Draws come both from our own ack and from the room broadcast, which
  // reaches the host too. Positions are unique per game, so keep the first.
  function recordDraw(draw: DrawnTopic) {
    if (!draws.value.some((known) => known.position === draw.position)) {
      draws.value.push(draw)
    }
  }

  // Takes what the server says about the game, replacing what we had.
  function applySnapshot(snapshot: GameSnapshot) {
    status.value = snapshot.status
    endReason.value = snapshot.end_reason
    players.value = snapshot.players
    draws.value = snapshot.draws
    prizes.value = snapshot.prizes
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

  // Joins from the join form.
  async function join(code: string, name: string): Promise<boolean> {
    return enterGame(code, name, 'fresh')
  }

  // Joins again with what the browser kept from this game, so a reload brings the player back
  // even if the server has not yet noticed the old page is gone.
  async function resume(code: string): Promise<boolean> {
    if (player.value?.code === code) {
      return true
    }
    const saved = savedSessionFor(code)
    if (!saved) {
      return false
    }
    return enterGame(code, saved.name, 'reload', saved.token)
  }

  // The one way into a game. What a refusal or an unreachable server does depends on how the join
  // started, and is decided in JOIN_FAILURES; nothing is thrown.
  async function enterGame(
    code: string,
    name: string,
    how: JoinStart,
    token: string | null = null,
  ): Promise<boolean> {
    error.value = null
    if (how === 'fresh') {
      ticket.value = null
    }
    let result
    try {
      result = await net.send('join_game', { code, name, rejoin_token: token })
    } catch {
      failJoin(JOIN_FAILURES[how].unreachable, UNREACHABLE)
      return false
    }
    if (!result.ok) {
      failJoin(JOIN_FAILURES[how].refused, messageFor(result.error))
      return false
    }
    enter(code, result)
    return true
  }

  function failJoin(failure: JoinFailure, message: string) {
    if (failure === 'leave') {
      leave({ error: message })
    } else if (failure === 'error') {
      error.value = message
    } else {
      actionError.value = message
    }
  }

  // The player is no longer in the game: another window took them over, or the server refused
  // to let them back. They are asked to join again, so nothing of theirs is kept.
  function leave(reason: { replaced: true } | { error: string }) {
    player.value = null
    ticket.value = null
    ticks.value = []
    pendingClaims.value = []
    rejoinToken = ''
    forgetSession()
    if ('replaced' in reason) {
      replaced.value = true
    } else {
      error.value = reason.error
    }
  }

  // The player is in: remember who they are, and take the game and their own state from the server.
  // The name is the one the game stored, which may differ in case or spaces from what was typed.
  function enter(code: string, snapshot: PlayerSnapshot) {
    const who = { code, name: snapshot.name }
    player.value = who
    replaced.value = false
    rejoinToken = snapshot.rejoin_token
    saveSession({ ...who, token: snapshot.rejoin_token })
    applyPlayerSnapshot(snapshot)
  }

  function applyPlayerSnapshot(snapshot: PlayerSnapshot) {
    applySnapshot(snapshot)
    ticket.value = snapshot.ticket
    ticks.value = snapshot.ticks
    // A claim that was waiting before and is decided now settled while this client was away:
    // its result is the last decided claim for that prize.
    const settledAway = pendingClaims.value.filter((prize) => !snapshot.pending_claims.includes(prize))
    pendingClaims.value = snapshot.pending_claims
    for (const prize of settledAway) {
      const decided = snapshot.decided_claims.filter((claim) => claim.prize === prize).at(-1)
      if (decided) {
        settleClaim(decided)
      }
    }
  }

  // A dropped socket is a new socket to the server, which acts only for players who joined on it.
  // The player rejoins with their token, and the host watches again.
  async function recover() {
    if (player.value) {
      await enterGame(player.value.code, player.value.name, 'reconnect', rejoinToken)
    } else if (hostLink.value) {
      await watchAsHost(hostLink.value)
    }
  }


  // Claims a prize. A valid claim waits in the prize's settlement window, so it is pending until
  // `claim_settled` arrives. It is pending from the moment it is sent, since the window can close
  // before the acknowledgement arrives. Winners are announced to the room, which updates the board.
  async function claimPrize(prize: Prize) {
    if (!player.value || isPending(prize)) {
      return
    }
    pendingClaims.value = [...pendingClaims.value, prize]
    actionError.value = null
    const dropPending = () => {
      pendingClaims.value = pendingClaims.value.filter((known) => known !== prize)
    }
    try {
      const result = await net.send('claim_prize', { prize })
      if (!result.ok) {
        dropPending()
        actionError.value = messageFor(result.error)
      }
    } catch {
      // The claim may still have reached the server: a rejoin's snapshot says if it is waiting.
      dropPending()
      actionError.value = UNREACHABLE
    }
  }

  // Ticks the topic if it isn't ticked, otherwise unticks it. The list changes only
  // once the server agrees.
  async function toggleTick(topic: string) {
    if (!player.value) {
      return
    }
    const isTicked = ticks.value.includes(topic)
    const result = await attempt(() =>
      net.send(isTicked ? 'untick_topic' : 'tick_topic', { topic }),
    )
    if (!result?.ok) {
      return
    }
    ticks.value = isTicked
      ? ticks.value.filter((known) => known !== topic)
      : [...ticks.value, topic]
  }

  async function watchAsHost(link: HostLink) {
    error.value = null
    hostLink.value = link
    const result = await net.send('watch_lobby', link)
    if (!result.ok) {
      error.value = messageFor(result.error)
      return
    }
    applySnapshot(result)
    claims.value = result.claims
    pool.value = result.pool.columns
    poolName.value = result.pool_name
    windowOpen.value = result.window_open
  }

  async function start(link: HostLink) {
    if (await attempt(() => net.send('start_game', link))) {
      status.value = 'started'
    }
  }

  async function end(link: HostLink) {
    if (await attempt(() => net.send('end_game', link))) {
      recordEnd('host')
    }
  }

  async function drawNext(link: HostLink) {
    const result = await attempt(() => net.send('draw_topic', link))
    if (result?.ok) {
      recordDraw(result.draw)
    }
  }

  return {
    status,
    started,
    ended,
    endReason,
    players,
    draws,
    drawnNames,
    prizes,
    isAwarded,
    error,
    actionError,
    messageFor,
    create,
    player,
    ticket,
    ticks,
    replaced,
    pendingClaims,
    isPending,
    join,
    resume,
    toggleTick,
    claimPrize,
    hostLink,
    claims,
    pool,
    poolName,
    windowOpen,
    watchAsHost,
    start,
    end,
    drawNext,
  }
})
