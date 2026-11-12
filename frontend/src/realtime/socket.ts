import { io, type Socket } from 'socket.io-client'
import type { components } from '../api/schema'

// Every message shape is generated from the server's models. Nothing is typed by hand here.
type Schemas = components['schemas']

export type HostLink = Schemas['HostLink']
// One player in one game, as the server addresses them: the game code and their display name.
export type PlayerRef = Schemas['JoinPayload']
export type DrawnTopic = Schemas['DrawAnnouncement']
export type PrizeBoardEntry = Schemas['PrizeBoardEntry']
export type PrizeAward = Schemas['PrizeAwarded']
export type ClaimLogEntry = Schemas['ClaimLogEntry']
export type GameEnd = Schemas['GameEnded']
export type ErrorCode = Schemas['ErrorCode']
export type Refusal = Schemas['Refusal']

export type JoinAck = Schemas['JoinAck']
export type JoinResult = JoinAck | Refusal
export type WatchResult = Schemas['WatchAck'] | Refusal
export type StartResult = Schemas['Accepted'] | Refusal
export type EndResult = Schemas['Accepted'] | Refusal
export type DrawResult = Schemas['DrawAck'] | Refusal
// A tick changes only the player's own list, so the server says only whether it happened.
export type TickResult = Schemas['Accepted'] | Refusal
export type ClaimResult = Schemas['Accepted'] | Refusal

// Event name → what the client sends and what the server acknowledges with.
type Commands = {
  join_game: [Schemas['JoinPayload'], JoinResult]
  watch_lobby: [HostLink, WatchResult]
  start_game: [HostLink, StartResult]
  draw_topic: [HostLink, DrawResult]
  end_game: [HostLink, EndResult]
  tick_topic: [Schemas['TickPayload'], TickResult]
  untick_topic: [Schemas['TickPayload'], TickResult]
  claim_prize: [Schemas['ClaimPayload'], ClaimResult]
}

// Event name → what the server announces to a room.
type Announcements = {
  lobby_updated: Schemas['LobbyUpdated']
  game_started: Schemas['GameStarted']
  game_ended: GameEnd
  topic_drawn: DrawnTopic
  prize_awarded: PrizeAward
  // Sent to the host only.
  claim_logged: ClaimLogEntry
}

let socket: Socket | null = null

function connection(): Socket {
  if (!socket) {
    socket = io({ path: '/socket.io' })
  }
  return socket
}

function send<E extends keyof Commands>(event: E, payload: Commands[E][0]): Promise<Commands[E][1]> {
  return connection().emitWithAck(event, payload) as Promise<Commands[E][1]>
}

function listen<E extends keyof Announcements>(event: E, handler: (data: Announcements[E]) => void): void {
  connection().on(event as string, handler as (data: unknown) => void)
}

export function joinGame(code: string, name: string): Promise<JoinResult> {
  return send('join_game', { code, name })
}

export function watchLobby(link: HostLink): Promise<WatchResult> {
  return send('watch_lobby', link)
}

export function startGame(link: HostLink): Promise<StartResult> {
  return send('start_game', link)
}

export function endGame(link: HostLink): Promise<EndResult> {
  return send('end_game', link)
}

export function drawTopic(link: HostLink): Promise<DrawResult> {
  return send('draw_topic', link)
}

// Ticks and claims name no player: the server acts for whoever joined on this socket.
export function tickTopic(topic: string): Promise<TickResult> {
  return send('tick_topic', { topic })
}

export function untickTopic(topic: string): Promise<TickResult> {
  return send('untick_topic', { topic })
}

// A valid claim is announced to the whole room, and a refused one answers only the claimant.
export function claimPrize(prize: string): Promise<ClaimResult> {
  return send('claim_prize', { prize })
}

export function onPrizeAwarded(handler: (award: PrizeAward) => void): void {
  listen('prize_awarded', handler)
}

// Every claim as it is decided, accepted or refused. The server tells only the host.
export function onClaimLogged(handler: (claim: ClaimLogEntry) => void): void {
  listen('claim_logged', handler)
}

export function onLobbyUpdated(handler: (players: string[]) => void): void {
  listen('lobby_updated', (data) => handler(data.players))
}

export function onGameStarted(handler: () => void): void {
  listen('game_started', () => handler())
}

export function onGameEnded(handler: (end: GameEnd) => void): void {
  listen('game_ended', handler)
}

export function onTopicDrawn(handler: (draw: DrawnTopic) => void): void {
  listen('topic_drawn', handler)
}

// Fires each time the connection comes back after a drop. The server forgets who a
// socket was when it drops, so the player must join again to act.
export function onReconnect(handler: () => void): void {
  connection().io.on('reconnect', () => {
    handler()
  })
}
