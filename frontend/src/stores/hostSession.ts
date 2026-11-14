import { ref } from 'vue'
import { messageFor, UNREACHABLE } from '../utils/errors'
import type {
  ClaimLogEntry,
  HostLink,
  HostSnapshot,
} from '../realtime/protocol'
import type { GameSession } from './gameSession'

export function createHostSession(game: GameSession) {
  const { net, error } = game
  const hostLink = ref<HostLink | null>(null)
  const claims = ref<ClaimLogEntry[]>([])
  const pool = ref<HostSnapshot['pool']['columns'] | null>(null)
  const poolName = ref<string | null>(null)
  const windowOpen = ref(false)

  // Opening the dashboard cannot show anything without the server, so its failure takes the page.
  // Winning the connection back is different: the page stays up and the failure is an action error.
  async function watch(link: HostLink, failure: 'error' | 'actionError') {
    error.value = null
    hostLink.value = link
    game.roles.add('host')
    let result
    try {
      result = await net.send('watch_lobby', link)
    } catch {
      game[failure].value = UNREACHABLE
      return
    }
    if (!result.ok) {
      game[failure].value = messageFor(result.error)
      return
    }
    game.applySnapshot(result)
    claims.value = result.claims
    pool.value = result.pool.columns
    poolName.value = result.pool_name
    windowOpen.value = result.window_open
  }

  function watchAsHost(link: HostLink) {
    return watch(link, 'error')
  }

  async function reconnect() {
    if (hostLink.value) {
      await watch(hostLink.value, 'actionError')
    }
  }

  // The host acts through the link it is watching with; before watching there is nothing to act on.
  async function start() {
    const link = hostLink.value
    if (link && (await game.attempt(() => net.send('start_game', link)))) {
      game.status.value = 'started'
    }
  }

  async function end() {
    const link = hostLink.value
    if (link && (await game.attempt(() => net.send('end_game', link)))) {
      game.recordEnd('host')
    }
  }

  async function drawNext() {
    const link = hostLink.value
    if (!link) {
      return
    }
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

  return {
    hostLink,
    claims,
    pool,
    poolName,
    windowOpen,
    watchAsHost,
    reconnect,
    start,
    end,
    drawNext,
  }
}
