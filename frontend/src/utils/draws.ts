import type { DrawnTopic } from '../realtime/protocol'

export function newestDrawsFirst(draws: readonly DrawnTopic[]): DrawnTopic[] {
  return [...draws].sort((a, b) => b.position - a.position)
}
