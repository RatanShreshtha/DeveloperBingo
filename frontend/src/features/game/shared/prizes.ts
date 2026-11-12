import type { components } from './api/schema'

export type Prize = components['schemas']['Prize']

// The words a player reads for each prize. A new prize without a label is a type error.
export const PRIZE_LABELS: Record<Prize, string> = {
  early_five: 'Early five',
  top_line: 'Top line',
  middle_line: 'Middle line',
  bottom_line: 'Bottom line',
  four_corners: 'Four corners',
  full_house: 'Full house',
}
