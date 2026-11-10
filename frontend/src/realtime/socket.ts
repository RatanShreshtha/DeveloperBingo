import { io, type Socket } from 'socket.io-client'

export type JoinResult = { ok: true } | { ok: false; error: string }
export type WatchResult =
  | { ok: true; players: string[] }
  | { ok: false; error: string }

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

export function onLobbyUpdated(handler: (players: string[]) => void): void {
  connection().on('lobby_updated', (data: { players: string[] }) => {
    handler(data.players)
  })
}
