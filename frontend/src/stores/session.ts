import { defineStore, storeToRefs } from 'pinia'
import { reactive } from 'vue'
import { createGameSession } from './gameSession'
import { createHostSession } from './hostSession'
import { createPlayerSession } from './playerSession'

// One Pinia instance owns the transport listeners and both role implementations. It lists each
// field once; the role views below name the fields they read.
const useSessionStore = defineStore('session', () => {
  const game = createGameSession()
  const player = createPlayerSession(game)
  const host = createHostSession(game)

  game.net.listen('game_ended', (end) => {
    game.recordEnd(end.reason)
  })
  game.net.onReconnect(async () => {
    // A tab that joined a game reconnects as its player. Only a tab with no player reconnects as
    // host, so a tab holding both roles recovers its player alone.
    if (game.roles.has('player')) {
      await player.reconnect()
    } else {
      await host.reconnect()
    }
  })

  return {
    status: game.status,
    started: game.started,
    ended: game.ended,
    endReason: game.endReason,
    players: game.players,
    draws: game.draws,
    drawnNames: game.drawnNames,
    prizes: game.prizes,
    error: game.error,
    actionError: game.actionError,
    player: player.player,
    ticket: player.ticket,
    ticks: player.ticks,
    replaced: player.replaced,
    pendingClaims: player.pendingClaims,
    isPending: player.isPending,
    join: player.join,
    resume: player.resume,
    toggleTick: player.toggleTick,
    claimPrize: player.claimPrize,
    hostLink: host.hostLink,
    claims: host.claims,
    pool: host.pool,
    poolName: host.poolName,
    windowOpen: host.windowOpen,
    watchAsHost: host.watchAsHost,
    start: host.start,
    end: host.end,
    drawNext: host.drawNext,
  }
})

type SessionStore = ReturnType<typeof useSessionStore>

// The fields both roles' views read. Each view is built from its own list, which starts with these.
const SHARED_VIEW = [
  'status',
  'started',
  'ended',
  'endReason',
  'players',
  'draws',
  'prizes',
  'error',
  'actionError',
] as const satisfies readonly (keyof SessionStore)[]

const PLAYER_VIEW = [
  ...SHARED_VIEW,
  'drawnNames',
  'player',
  'ticket',
  'ticks',
  'replaced',
  'pendingClaims',
  'isPending',
  'join',
  'resume',
  'toggleTick',
  'claimPrize',
] as const satisfies readonly (keyof SessionStore)[]

const HOST_VIEW = [
  ...SHARED_VIEW,
  'hostLink',
  'claims',
  'pool',
  'poolName',
  'windowOpen',
  'watchAsHost',
  'start',
  'end',
  'drawNext',
] as const satisfies readonly (keyof SessionStore)[]

// The named fields of the store, as refs for state and getters and as functions for actions,
// kept reactive for the view.
function viewOf<K extends keyof SessionStore>(
  store: SessionStore,
  fields: readonly K[],
): Pick<SessionStore, K> {
  const refs: Partial<Record<keyof SessionStore, unknown>> = storeToRefs(store)
  const view = Object.fromEntries(
    fields.map((field) => [field, field in refs ? refs[field] : store[field]]),
  )
  return reactive(view) as Pick<SessionStore, K>
}

export function usePlayerSession() {
  return viewOf(useSessionStore(), PLAYER_VIEW)
}

export function useHostSession() {
  return viewOf(useSessionStore(), HOST_VIEW)
}
