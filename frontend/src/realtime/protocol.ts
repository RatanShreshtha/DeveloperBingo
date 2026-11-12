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

export type JoinResult = PlayerSnapshot | Refusal
export type WatchResult = HostSnapshot | Refusal
export type DrawResult = Schemas['DrawAck'] | Refusal
// A tick changes only the player's own list, so the server says only whether it happened.
// A command that only says whether it happened: start, end, tick, untick and claim.
export type Done = Schemas['Accepted'] | Refusal

// Event name → what the client sends and what the server acknowledges with.
export type Commands = {
  join_game: [Schemas['JoinPayload'], JoinResult]
  watch_lobby: [HostLink, WatchResult]
  start_game: [HostLink, Done]
  draw_topic: [HostLink, DrawResult]
  end_game: [HostLink, Done]
  tick_topic: [Schemas['TickPayload'], Done]
  untick_topic: [Schemas['TickPayload'], Done]
  claim_prize: [Schemas['ClaimPayload'], Done]
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
