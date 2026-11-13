import { defineStore, storeToRefs } from 'pinia'
import { reactive } from 'vue'
import { createGameSession } from './gameSession'
import { createHostSession } from './hostSession'
import { createPlayerSession } from './playerSession'

// One Pinia instance owns the transport listeners and both role implementations.
const useSessionStore = defineStore('session', () => {
  const game = createGameSession()
  const player = createPlayerSession(game)
  const host = createHostSession(game)

  game.net.listen('game_ended', (end) => {
    game.recordEnd(end.reason)
  })
  game.net.onReconnect(async () => {
    if (player.player.value) {
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

export function usePlayerSession() {
  const store = useSessionStore()
  const {
    status,
    started,
    ended,
    endReason,
    players,
    draws,
    drawnNames,
    prizes,
    error,
    actionError,
    player,
    ticket,
    ticks,
    replaced,
    pendingClaims,
  } = storeToRefs(store)
  return reactive({
    status,
    started,
    ended,
    endReason,
    players,
    draws,
    drawnNames,
    prizes,
    error,
    actionError,
    player,
    ticket,
    ticks,
    replaced,
    pendingClaims,
    isPending: store.isPending,
    join: store.join,
    resume: store.resume,
    toggleTick: store.toggleTick,
    claimPrize: store.claimPrize,
  })
}

export function useHostSession() {
  const store = useSessionStore()
  const {
    status,
    started,
    ended,
    endReason,
    players,
    draws,
    prizes,
    error,
    actionError,
    hostLink,
    claims,
    pool,
    poolName,
    windowOpen,
  } = storeToRefs(store)
  return reactive({
    status,
    started,
    ended,
    endReason,
    players,
    draws,
    prizes,
    error,
    actionError,
    hostLink,
    claims,
    pool,
    poolName,
    windowOpen,
    watchAsHost: store.watchAsHost,
    start: store.start,
    end: store.end,
    drawNext: store.drawNext,
  })
}
