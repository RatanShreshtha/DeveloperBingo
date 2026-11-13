import type { GameEnd } from '../realtime/protocol'

// What each person is told when the game is over, by who is reading. `history` is the third-person
// line on a finished game's stored record, read by anyone with its code.
export const END_MESSAGES: Record<'host' | 'player' | 'history', Record<GameEnd['reason'], string>> = {
  host: {
    full_house: 'The game is over: the full house was claimed.',
    host: 'You ended the game.',
  },
  player: {
    full_house: 'The game is over: the full house was claimed.',
    host: 'The host ended the game.',
  },
  history: {
    full_house: 'The full house was claimed.',
    host: 'The host ended the game.',
  },
}
