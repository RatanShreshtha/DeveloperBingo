import { ref } from 'vue'
import { messageFor } from '../utils/errors'
import type { ClaimLogEntry, HostLink, HostSnapshot } from '../realtime/protocol'
import type { GameSession } from './gameSession'

export function createHostSession(game: GameSession) {
  const { net, error } = game
  const hostLink = ref<HostLink | null>(null)
  const claims = ref<ClaimLogEntry[]>([])
  const pool = ref<HostSnapshot['pool']['columns'] | null>(null)
  const poolName = ref<string | null>(null)
  const windowOpen = ref(false)

  function closeWindow() {
    windowOpen.value = false
  }

  async function watchAsHost(link: HostLink) {
    error.value = null
    hostLink.value = link
    const result = await net.send('watch_lobby', link)
    if (!result.ok) {
      error.value = messageFor(result.error)
      return
    }
    game.applySnapshot(result)
    claims.value = result.claims
    pool.value = result.pool.columns
    poolName.value = result.pool_name
    windowOpen.value = result.window_open
  }

  async function reconnect() {
    if (hostLink.value) {
      await watchAsHost(hostLink.value)
    }
  }

  async function start(link: HostLink) {
    if (await game.attempt(() => net.send('start_game', link))) {
      game.status.value = 'started'
    }
  }

  async function end(link: HostLink) {
    if (await game.attempt(() => net.send('end_game', link))) {
      game.recordEnd('host')
      closeWindow()
    }
  }

  async function drawNext(link: HostLink) {
    const result = await game.attempt(() => net.send('draw_topic', link))
    if (result?.ok) {
      game.recordDraw(result.draw)
    }
  }

  net.listen('claim_logged', (claim) => {
    claims.value.push(claim)
  })
  net.listen('window_changed', (change) => {
    windowOpen.value = change.open
  })

  return { hostLink, claims, pool, poolName, windowOpen, closeWindow, watchAsHost, reconnect, start, end, drawNext }
}
