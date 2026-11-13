import type {
  Announcements,
  CommandName,
  Commands,
  EventName,
} from '../realtime/protocol'
import { useTransport, type Transport } from '../realtime/transport'

type Reply<E extends CommandName> =
  | Commands[E][1]
  | ((payload: Commands[E][0]) => Commands[E][1] | Promise<Commands[E][1]>)

/**
 * A scripted server for tests. Give each command the reply it should get, emit an event as the
 * server would, and drop and restore the connection. Tests then assert on store state.
 */
export class FakeTransport implements Transport {
  /** Every command sent, in order. */
  readonly sent: { event: CommandName; payload: unknown }[] = []
  private readonly replies = new Map<CommandName, Reply<CommandName>>()
  private readonly listeners = new Map<EventName, ((data: never) => void)[]>()
  private readonly reconnectHandlers: (() => void | Promise<void>)[] = []

  /** What the server answers each time this command arrives. */
  answer<E extends CommandName>(event: E, reply: Reply<E>): void {
    this.replies.set(event, reply as Reply<CommandName>)
  }

  /** The payloads sent with this command, in order. */
  payloads<E extends CommandName>(event: E): Commands[E][0][] {
    return this.sent
      .filter((call) => call.event === event)
      .map((call) => call.payload as Commands[E][0])
  }

  async send<E extends CommandName>(
    event: E,
    payload: Commands[E][0],
  ): Promise<Commands[E][1]> {
    this.sent.push({ event, payload })
    const reply = this.replies.get(event)
    if (reply === undefined) {
      throw new Error(`The fake server has no reply for "${event}"`)
    }
    return (
      typeof reply === 'function' ? reply(payload as never) : reply
    ) as Commands[E][1]
  }

  listen<E extends EventName>(
    event: E,
    handler: (data: Announcements[E]) => void,
  ): void {
    this.listeners.set(event, [
      ...(this.listeners.get(event) ?? []),
      handler as (data: never) => void,
    ])
  }

  onReconnect(handler: () => void | Promise<void>): void {
    this.reconnectHandlers.push(handler)
  }

  /** The server announces an event to this client. */
  emit<E extends EventName>(event: E, data: Announcements[E]): void {
    for (const handler of this.listeners.get(event) ?? []) {
      handler(data as never)
    }
  }

  /** The connection drops and comes back; resolves once the store has finished recovering. */
  async reconnect(): Promise<void> {
    await Promise.all(this.reconnectHandlers.map((handler) => handler()))
  }
}

/** Makes a fresh fake the transport every store uses. Call it before creating the store. */
export function installFakeTransport(): FakeTransport {
  const fake = new FakeTransport()
  useTransport(fake)
  return fake
}
