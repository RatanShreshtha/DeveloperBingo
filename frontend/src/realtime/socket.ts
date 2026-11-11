import { io, type Socket } from 'socket.io-client'
import type { components } from '../api/schema'

// The private handle on one game: whoever holds it can control that game.
export type HostLink = { code: string; token: string }

// Shapes the server sends, generated from its models.
export type DrawnTopic = components['schemas']['DrawAnnouncement']

// Shapes the server sends only over the socket, hand-typed for now.
export type TicketCells = (string | null)[][]
// Each prize, and who it was awarded to, or null while it is still open.
export type PrizeBoard = Record<string, string | null>
export type PrizeAward = { prize: string; winner: string }
// A rejoin also gets back the ticks the player already had.
export type JoinResult =
  | { ok: true; ticket: TicketCells; ticks: string[]; prizes: PrizeBoard }
  | { ok: false; error: string }
export type WatchResult =
  | { ok: true; players: string[]; prizes: PrizeBoard }
  | { ok: false; error: string }
export type ClaimResult = { ok: true } | { ok: false; error: string }
export type StartResult = { ok: true } | { ok: false; error: string }
export type DrawResult = { ok: true; draw: DrawnTopic } | { ok: false; error: string }
// One player in one game, as the server addresses them: the game code and their display name.
export type PlayerRef = { code: string; name: string }
// A tick changes only the player's own list, so the server says only whether it happened.
export type TickResult = { ok: true } | { ok: false; error: string }

let socket: Socket | null = null

function connection(): Socket {
  if (!socket) {
    socket = io({ path: '/socket.io' })
  }
  return socket
}

function hostPayload(link: HostLink) {
  return { code: link.code, host_token: link.token }
}

export function joinGame(code: string, name: string): Promise<JoinResult> {
  return connection().emitWithAck('join_game', { code, name }) as Promise<JoinResult>
}

export function watchLobby(link: HostLink): Promise<WatchResult> {
  return connection().emitWithAck('watch_lobby', hostPayload(link)) as Promise<WatchResult>
}

export function startGame(link: HostLink): Promise<StartResult> {
  return connection().emitWithAck('start_game', hostPayload(link)) as Promise<StartResult>
}

export function drawTopic(link: HostLink): Promise<DrawResult> {
  return connection().emitWithAck('draw_topic', hostPayload(link)) as Promise<DrawResult>
}

// A player's ticks are private, so each call answers only the sender, and no ticks come back.
function playerPayload(player: PlayerRef) {
  return { code: player.code, name: player.name }
}

export function tickTopic(player: PlayerRef, topic: string): Promise<TickResult> {
  return connection().emitWithAck('tick_topic', { ...playerPayload(player), topic }) as Promise<TickResult>
}

export function untickTopic(player: PlayerRef, topic: string): Promise<TickResult> {
  return connection().emitWithAck('untick_topic', { ...playerPayload(player), topic }) as Promise<TickResult>
}

// A valid claim is announced to the whole room, and a refused one answers only the claimant.
export function claimPrize(player: PlayerRef, prize: string): Promise<ClaimResult> {
  return connection().emitWithAck('claim_prize', { ...playerPayload(player), prize }) as Promise<ClaimResult>
}

export function onPrizeAwarded(handler: (award: PrizeAward) => void): void {
  connection().on('prize_awarded', (data: PrizeAward) => {
    handler(data)
  })
}

export function onLobbyUpdated(handler: (players: string[]) => void): void {
  connection().on('lobby_updated', (data: { players: string[] }) => {
    handler(data.players)
  })
}

export function onGameStarted(handler: () => void): void {
  connection().on('game_started', () => {
    handler()
  })
}

export function onTopicDrawn(handler: (draw: DrawnTopic) => void): void {
  connection().on('topic_drawn', (data: DrawnTopic) => {
    handler(data)
  })
}

// Fires each time the connection comes back after a drop. The server forgets who a
// socket was when it drops, so the player must join again to act.
export function onReconnect(handler: () => void): void {
  connection().io.on('reconnect', () => {
    handler()
  })
}
