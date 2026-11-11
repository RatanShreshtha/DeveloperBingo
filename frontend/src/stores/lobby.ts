import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { createGame, fetchDrawHistory } from '../api/games'
import { EARLY_FIVE } from '../prizes'
import {
  claimPrize as sendClaim,
  drawTopic,
  joinGame,
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
  type HostLink,
  type JoinResult,
  type PlayerRef,
  type PrizeBoard,
  type TicketCells,
} from '../realtime/socket'

const ERROR_MESSAGES: Record<string, string> = {
  name_taken: 'That name is already taken in this game',
  already_joined: 'You have already joined a game from this window',
  game_full: 'This game is full',
  already_started: 'This game has already started',
  not_found: 'No game found with that code',
  not_host: 'This host link is not valid for this game',
  not_started: 'The game has not started yet',
  no_topics_left: 'Every topic has already been drawn',
  not_drawn: 'That topic has not been drawn yet',
  not_on_ticket: 'That topic is not on your ticket',
  not_a_player: 'You are not in this game',
  not_joined: 'You have not joined this game from this window',
  not_won: 'This claim does not complete the prize yet',
  prize_taken: 'Someone has already been awarded this prize',
  unknown_prize: 'That prize does not exist',
}

function messageFor(code: string): string {
  return ERROR_MESSAGES[code] ?? 'Something went wrong. Please try again.'
}

type Refusable = { ok: true } | { ok: false; error: string }

export const useLobbyStore = defineStore('lobby', () => {
  const players = ref<string[]>([])
  const ticket = ref<TicketCells | null>(null)
  const started = ref(false)
  const draws = ref<DrawnTopic[]>([])
  // This player's own identity in the game, and the topics they have ticked.
  const player = ref<PlayerRef | null>(null)
  const ticks = ref<string[]>([])
  const drawnNames = computed(() => draws.value.map((draw) => draw.name))
  // Who each prize was awarded to, or null while it is still open.
  const prizes = ref<PrizeBoard>({ [EARLY_FIVE]: null })
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
  onTopicDrawn(recordDraw)
  onReconnect(rejoin)
  onPrizeAwarded((award) => {
    prizes.value = { ...prizes.value, [award.prize]: award.winner }
  })

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
      actionError.value = messageFor((result as { error: string }).error)
      return null
    }
    return result
  }

  async function create() {
    return createGame()
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
  function restore(result: Extract<JoinResult, { ok: true }>) {
    ticket.value = result.ticket
    ticks.value = result.ticks
    prizes.value = result.prizes
  }

  // Claims a prize. A valid claim is announced to the room, which updates the board.
  async function claimPrize(prize: string) {
    const who = player.value
    if (!who) {
      return
    }
    await attempt(() => sendClaim(who, prize))
  }

  // Ticks the topic if it isn't ticked, otherwise unticks it. The list changes only
  // once the server agrees.
  async function toggleTick(topic: string) {
    const who = player.value
    if (!who) {
      return
    }
    const isTicked = ticks.value.includes(topic)
    const send = isTicked ? untickTopic : tickTopic
    const result = await attempt(() => send(who, topic))
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
    draws,
    drawnNames,
    player,
    ticks,
    prizes,
    error,
    actionError,
    create,
    join,
    toggleTick,
    claimPrize,
    watchAsHost,
    loadDrawHistory,
    start,
    drawNext,
  }
})
