import { ref } from 'vue'
import { messageFor, UNREACHABLE } from '../features/game/shared/errors'
import type { Prize } from '../features/game/shared/prizes'
import type { ClaimSettled, PlayerRef, PlayerSnapshot } from '../realtime/protocol'
import { forgetSession, saveSession, savedSessionFor } from '../realtime/savedSession'
import type { GameSession } from './gameSession'

type JoinStart = 'fresh' | 'reload' | 'reconnect'
type JoinFailure = 'leave' | 'error' | 'actionError'

// An unreachable server does not establish that the player has left the game.
const JOIN_FAILURES: Record<JoinStart, { refused: JoinFailure; unreachable: JoinFailure }> = {
  fresh: { refused: 'error', unreachable: 'error' },
  reload: { refused: 'leave', unreachable: 'error' },
  reconnect: { refused: 'leave', unreachable: 'actionError' },
}

export function createPlayerSession(game: GameSession) {
  const { net, error, actionError } = game
  const player = ref<PlayerRef | null>(null)
  const ticket = ref<PlayerSnapshot['ticket'] | null>(null)
  const ticks = ref<string[]>([])
  let rejoinToken = ''
  const replaced = ref(false)
  const pendingClaims = ref<Prize[]>([])
  const isPending = (prize: Prize) => pendingClaims.value.includes(prize)

  function settleClaim(claim: ClaimSettled) {
    pendingClaims.value = pendingClaims.value.filter((known) => known !== claim.prize)
    if (!claim.accepted && claim.error) {
      actionError.value = messageFor(claim.error)
    }
  }

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

  function failJoin(failure: JoinFailure, message: string) {
    if (failure === 'leave') {
      leave({ error: message })
    } else if (failure === 'error') {
      error.value = message
    } else {
      actionError.value = message
    }
  }

  function applyPlayerSnapshot(snapshot: PlayerSnapshot) {
    game.applySnapshot(snapshot)
    ticket.value = snapshot.ticket
    ticks.value = snapshot.ticks
    // Claims settled while disconnected are reported in the new snapshot.
    const settledAway = pendingClaims.value.filter((prize) => !snapshot.pending_claims.includes(prize))
    pendingClaims.value = snapshot.pending_claims
    for (const prize of settledAway) {
      const decided = snapshot.decided_claims.filter((claim) => claim.prize === prize).at(-1)
      if (decided) {
        settleClaim(decided)
      }
    }
  }

  function enter(code: string, snapshot: PlayerSnapshot) {
    const who = { code, name: snapshot.name }
    player.value = who
    replaced.value = false
    rejoinToken = snapshot.rejoin_token
    saveSession({ ...who, token: snapshot.rejoin_token })
    applyPlayerSnapshot(snapshot)
  }

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

  function join(code: string, name: string): Promise<boolean> {
    return enterGame(code, name, 'fresh')
  }

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

  async function reconnect() {
    if (player.value) {
      await enterGame(player.value.code, player.value.name, 'reconnect', rejoinToken)
    }
  }

  // Mark the claim pending before sending: settlement may precede the acknowledgement.
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
      // The next snapshot determines whether the claim reached the server.
      dropPending()
      actionError.value = UNREACHABLE
    }
  }

  async function toggleTick(topic: string) {
    if (!player.value) {
      return
    }
    const isTicked = ticks.value.includes(topic)
    const result = await game.attempt(() =>
      net.send(isTicked ? 'untick_topic' : 'tick_topic', { topic }),
    )
    if (!result?.ok) {
      return
    }
    ticks.value = isTicked
      ? ticks.value.filter((known) => known !== topic)
      : [...ticks.value, topic]
  }

  net.listen('claim_settled', settleClaim)
  net.listen('replaced', () => leave({ replaced: true }))

  return { player, ticket, ticks, replaced, pendingClaims, isPending, join, resume, reconnect, toggleTick, claimPrize }
}
