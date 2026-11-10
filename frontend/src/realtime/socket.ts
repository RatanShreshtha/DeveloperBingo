import { io, type Socket } from 'socket.io-client'

export type TicketCells = (string | null)[][]
export type JoinResult =
  | { ok: true; ticket: TicketCells }
  | { ok: false; error: string }
export type WatchResult =
  | { ok: true; players: string[] }
  | { ok: false; error: string }
export type DrawnTopic = { position: number; name: string; explanation: string }
export type StartResult = { ok: true } | { ok: false; error: string }
export type DrawResult = { ok: true; draw: DrawnTopic } | { ok: false; error: string }

let socket: Socket | null = null

function connection(): Socket {
  if (!socket) {
    socket = io({ path: '/socket.io' })
  }
  return socket
}

export function joinGame(code: string, name: string): Promise<JoinResult> {
  return connection().emitWithAck('join_game', { code, name }) as Promise<JoinResult>
}

export function watchLobby(code: string, hostToken: string): Promise<WatchResult> {
  return connection().emitWithAck('watch_lobby', {
    code,
    host_token: hostToken,
  }) as Promise<WatchResult>
}

export function startGame(code: string, hostToken: string): Promise<StartResult> {
  return connection().emitWithAck('start_game', {
    code,
    host_token: hostToken,
  }) as Promise<StartResult>
}

export function drawTopic(code: string, hostToken: string): Promise<DrawResult> {
  return connection().emitWithAck('draw_topic', {
    code,
    host_token: hostToken,
  }) as Promise<DrawResult>
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
