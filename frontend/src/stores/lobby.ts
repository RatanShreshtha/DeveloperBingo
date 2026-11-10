import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createGame } from '../api/games'
import { joinGame, onLobbyUpdated, watchLobby } from '../realtime/socket'

const ERROR_MESSAGES: Record<string, string> = {
  name_taken: 'That name is already taken in this game',
  game_full: 'This game is full',
  already_started: 'This game has already started',
  not_found: 'No game found with that code',
  not_host: 'This host link is not valid for this game',
}

function messageFor(code: string): string {
  return ERROR_MESSAGES[code] ?? 'Something went wrong. Please try again.'
}

export const useLobbyStore = defineStore('lobby', () => {
  const players = ref<string[]>([])
  const error = ref<string | null>(null)

  onLobbyUpdated((names) => {
    players.value = names
  })

  async function create() {
    return createGame()
  }

  async function join(code: string, name: string): Promise<boolean> {
    error.value = null
    const result = await joinGame(code, name)
    if (!result.ok) {
      error.value = messageFor(result.error)
      return false
    }
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

  return { players, error, create, join, watchAsHost }
})
