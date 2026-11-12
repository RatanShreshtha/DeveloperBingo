import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { createGame } from '../api/games'
import type { Prize } from '../prizes'
import type {
  ClaimLogEntry,
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

export function messageFor(code: ErrorCode): string {
  return ERROR_MESSAGES[code]
}

type Refusable = { ok: true } | Refusal
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
  // Tells a claim's own answer from an older one that a reconnect abandoned.
  const claimAttempts = new Map<Prize, number>()
  let attempts = 0

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
    windowOpen.value = false
  })
  net.listen('replaced', () => {
    replaced.value = true
    player.value = null
    forgetSession()
  })
  net.onReconnect(recover)

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

  async function join(code: string, name: string): Promise<boolean> {
    error.value = null
    ticket.value = null
    const result = await net.send('join_game', { code, name, rejoin_token: null })
    if (!result.ok) {
      error.value = messageFor(result.error)
      return false
    }
    enter({ code, name }, result)
    return true
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
    error.value = null
    const who = { code, name: saved.name }
    const result = await net.send('join_game', { ...who, rejoin_token: saved.token })
    if (!result.ok) {
      forgetSession()
      error.value = messageFor(result.error)
      return false
    }
    enter(who, result)
    return true
  }

  // The player is in: remember who they are, and take the game and their own state from the server.
  function enter(who: PlayerRef, snapshot: PlayerSnapshot) {
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
    // The old answers are lost with the old connection: claim again to get the held result.
    pendingClaims.value = []
    claimAttempts.clear()
    for (const prize of snapshot.pending_claims) {
      void sendClaim(prize)
    }
  }

  // A dropped socket is a new socket to the server, which acts only for players who joined on it.
  // The player rejoins with their token, and the host watches again.
  async function recover() {
    if (player.value) {
      await rejoin(player.value)
    } else if (hostLink.value) {
      await watchAsHost(hostLink.value)
    }
  }

  async function rejoin(who: PlayerRef) {
    const result = await net.send('join_game', { ...who, rejoin_token: rejoinToken })
    if (!result.ok) {
      actionError.value = messageFor(result.error)
      return
    }
    enter(who, result)
  }

  // Claims a prize. The server answers once the prize's settlement window closes, so the claim
  // is pending until then. Winners are announced to the room, which updates the board.
  async function claimPrize(prize: Prize) {
    if (!player.value || isPending(prize)) {
      return
    }
    await sendClaim(prize)
  }

  async function sendClaim(prize: Prize) {
    const mine = ++attempts
    claimAttempts.set(prize, mine)
    pendingClaims.value = [...pendingClaims.value.filter((known) => known !== prize), prize]
    try {
      await attempt(() => net.send('claim_prize', { prize }))
    } finally {
      if (claimAttempts.get(prize) === mine) {
        claimAttempts.delete(prize)
        pendingClaims.value = pendingClaims.value.filter((known) => known !== prize)
      }
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
