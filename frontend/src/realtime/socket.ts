import { io, type Socket } from 'socket.io-client'
import type { components } from '../api/schema'

// The private handle on one game: whoever holds it can control that game.
export type HostLink = { code: string; token: string }

// Shapes the server sends, generated from its models.
export type DrawnTopic = components['schemas']['DrawAnnouncement']

// Shapes the server sends only over the socket, hand-typed for now.
export type TicketCells = (string | null)[][]
export type JoinResult =
  | { ok: true; ticket: TicketCells }
  | { ok: false; error: string }
export type WatchResult =
  | { ok: true; players: string[] }
  | { ok: false; error: string }
export type StartResult = { ok: true } | { ok: false; error: string }
export type DrawResult = { ok: true; draw: DrawnTopic } | { ok: false; error: string }
export type TickResult = { ok: true; ticked: string[] } | { ok: false; error: string }

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

// A player's ticks are private to them, so each call answers only the sender.
export function tickTopic(code: string, name: string, topic: string): Promise<TickResult> {
  return connection().emitWithAck('tick_topic', { code, name, topic }) as Promise<TickResult>
}

export function untickTopic(code: string, name: string, topic: string): Promise<TickResult> {
  return connection().emitWithAck('untick_topic', { code, name, topic }) as Promise<TickResult>
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
