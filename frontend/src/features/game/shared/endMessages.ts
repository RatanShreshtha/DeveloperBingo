import type { GameEnd } from './realtime/protocol'

// What each person is told when the game is over, by who is reading.
export const END_MESSAGES: Record<'host' | 'player', Record<GameEnd['reason'], string>> = {
  host: {
    full_house: 'The game is over: the full house was claimed.',
    host: 'You ended the game.',
  },
  player: {
    full_house: 'The game is over: the full house was claimed.',
    host: 'The host ended the game.',
  },
}
