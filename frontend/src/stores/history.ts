import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchGameHistory, GameHistoryError, type GameHistoryResponse } from '../api/games'

export const useHistoryStore = defineStore('history', () => {
  const history = ref<GameHistoryResponse | null>(null)
  const error = ref<string | null>(null)

  async function load(code: string) {
    history.value = null
    error.value = null
    try {
      history.value = await fetchGameHistory(code)
    } catch (err) {
      if (err instanceof GameHistoryError && err.status === 404) {
        error.value = 'There is no stored history for this game'
      } else if (err instanceof GameHistoryError && err.status === 503) {
        error.value = 'Game history is unavailable right now. Try again shortly.'
      } else {
        error.value = 'Could not load the game history'
      }
    }
  }

  return { history, error, load }
})
