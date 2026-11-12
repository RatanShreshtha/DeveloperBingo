import { createPinia, setActivePinia } from 'pinia'
import { installFakeTransport } from './fakeTransport'
import { playerSnapshot } from './snapshots'
import type { PlayerSnapshot } from '../realtime/protocol'
import { usePlayerSession } from '../stores/session'

/** A fresh fake server, empty browser storage and a fresh store, as every view test starts. */
export function startFresh() {
  sessionStorage.clear()
  const fake = installFakeTransport()
  setActivePinia(createPinia())
  return fake
}

/** Ada has joined game ABC123 and the server answered with this snapshot. */
export async function joinedAda(
  fake: ReturnType<typeof installFakeTransport>,
  overrides: Partial<PlayerSnapshot> = {},
) {
  fake.answer('join_game', playerSnapshot(overrides))
  const store = usePlayerSession()
  await store.join('ABC123', 'Ada')
  return store
}
