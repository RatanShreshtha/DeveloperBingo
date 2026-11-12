import type { components } from '../api/schema'

// Every message shape is generated from the server's models. Nothing is typed by hand here.
type Schemas = components['schemas']

export type HostLink = Schemas['HostLink']
// One player in one game, as the server addresses them: the game code and their display name.
export type PlayerRef = { code: string; name: string }
export type GameSnapshot = Schemas['GameSnapshot']
export type PlayerSnapshot = Schemas['JoinAck']
export type HostSnapshot = Schemas['WatchAck']
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
export type Commands = {
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
export type Announcements = {
  lobby_updated: Schemas['LobbyUpdated']
  game_started: Schemas['GameStarted']
  game_ended: GameEnd
  topic_drawn: DrawnTopic
  prize_awarded: PrizeAward
  // Sent to the host only.
  claim_logged: ClaimLogEntry
  // Sent to one socket only: another socket took over its player.
  replaced: Schemas['Replaced']
}

export type CommandName = keyof Commands
export type EventName = keyof Announcements
