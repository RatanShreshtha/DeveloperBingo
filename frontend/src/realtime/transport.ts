import { io, type Socket } from 'socket.io-client'
import type {
  Announcements,
  CommandName,
  Commands,
  EventName,
} from './protocol'

/**
 * All the store needs from the network: send a command and await its reply, listen for an event
 * the server announces, and be told when a dropped connection comes back.
 */
export interface Transport {
  send<E extends CommandName>(
    event: E,
    payload: Commands[E][0],
  ): Promise<Commands[E][1]>
  listen<E extends EventName>(
    event: E,
    handler: (data: Announcements[E]) => void,
  ): void
  /** Fires each time the connection returns after a drop. The server forgets who a dropped socket was. */
  onReconnect(handler: () => void): void
}

/**
 * How long a command waits for the server's reply. Without a limit socket.io waits forever while
 * the server is down. When it runs out, socket.io drops the command from its send buffer, so it
 * is not replayed on reconnect, and `send` rejects.
 */
export const SEND_TIMEOUT_MS = 10_000

/** The socket.io adapter the app uses. It connects when first needed. */
export function socketIoTransport(): Transport {
  let socket: Socket | null = null
  const connection = (): Socket => (socket ??= io({ path: '/socket.io' }))
  return {
    send: (event, payload) =>
      connection().timeout(SEND_TIMEOUT_MS).emitWithAck(event, payload),
    listen: (event, handler) => {
      connection().on(event as string, handler as (data: unknown) => void)
    },
    onReconnect: (handler) => {
      connection().io.on('reconnect', () => handler())
    },
  }
}

let current: Transport | null = null

/** The transport in use: the socket.io one unless a test installed another. */
export function transport(): Transport {
  return (current ??= socketIoTransport())
}

export function useTransport(replacement: Transport | null): void {
  current = replacement
}
