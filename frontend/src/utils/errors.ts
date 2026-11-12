import type { ErrorCode } from '../realtime/protocol'

const ERROR_MESSAGES: Record<ErrorCode, string> = {
  name_taken: 'That name is already taken in this game',
  already_joined: 'You have already joined a game from this window',
  game_full: 'This game is full',
  already_started: 'This game has already started',
  game_ended: 'The game has ended',
  not_found: 'No game found with that code',
  not_host: 'This host link is not valid for this game',
  not_started: 'The game has not started yet',
  no_topics_left: 'Every topic has already been drawn',
  not_drawn: 'That topic has not been drawn yet',
  not_on_ticket: 'That topic is not on your ticket',
  not_a_player: 'You are not in this game',
  not_joined: 'You have not joined this game from this window',
  claim_not_valid: 'This claim does not complete the prize yet',
  prize_taken: 'Someone has already been awarded this prize',
  unknown_prize: 'That prize does not exist',
  settlement_open: 'A claim is being settled. Draws resume in a moment.',
  claim_pending: 'Your claim is waiting to be settled, so you cannot untick a topic now',
  invalid_message: 'That request was not understood. Please reload the page.',
}

export const UNREACHABLE = 'Could not reach the server. Check your connection and try again.'

export function messageFor(code: ErrorCode): string {
  return ERROR_MESSAGES[code]
}
