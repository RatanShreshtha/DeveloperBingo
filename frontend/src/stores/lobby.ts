import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createGame } from '../api/games'
import {
  drawTopic,
  getDrawHistory,
  joinGame,
  onGameStarted,
  onLobbyUpdated,
  onTopicDrawn,
  startGame,
  watchLobby,
  type DrawnTopic,
  type TicketCells,
} from '../realtime/socket'

const ERROR_MESSAGES: Record<string, string> = {
  name_taken: 'That name is already taken in this game',
  game_full: 'This game is full',
  already_started: 'This game has already started',
  not_found: 'No game found with that code',
  not_host: 'This host link is not valid for this game',
  not_started: 'The game has not started yet',
  no_topics_left: 'Every topic has already been drawn',
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
  // Problems loading the lobby, shown in place of it.
  const error = ref<string | null>(null)
  // Refusals of something the user did, shown next to the controls.
  const actionError = ref<string | null>(null)

  onLobbyUpdated((names) => {
    players.value = names
  })
  onGameStarted(() => {
    started.value = true
  })
  onTopicDrawn(recordDraw)

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
    ticket.value = result.ticket
    return true
  }

  async function watchAsHost(code: string, hostToken: string) {
    error.value = null
    const result = await watchLobby(code, hostToken)
    if (result.ok) {
      players.value = result.players
    } else {
      error.value = messageFor(result.error)
    }
  }

  async function loadDrawHistory(code: string) {
    error.value = null
    const result = await getDrawHistory(code)
    if (!result.ok) {
      error.value = messageFor(result.error)
      return
    }
    draws.value = [...result.draws]
    if (result.draws.length > 0) {
      started.value = true
    }
  }

  async function start(code: string, hostToken: string) {
    if (await attempt(() => startGame(code, hostToken))) {
      started.value = true
    }
  }

  async function drawNext(code: string, hostToken: string) {
    const result = await attempt(() => drawTopic(code, hostToken))
    if (result?.ok) {
      recordDraw(result.draw)
    }
  }

  return {
    players,
    ticket,
    started,
    draws,
    error,
    actionError,
    create,
    join,
    watchAsHost,
    loadDrawHistory,
    start,
    drawNext,
  }
})
