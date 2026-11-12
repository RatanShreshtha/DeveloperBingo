// What a player's browser keeps so that a reload can rejoin the game: the code, their name and the
// rejoin token the server issued. sessionStorage belongs to one tab, so two tabs are two players.
const KEY = 'devbingo:player'

export type SavedSession = { code: string; name: string; token: string }

export function saveSession(session: SavedSession): void {
  sessionStorage.setItem(KEY, JSON.stringify(session))
}

/** The saved session, if it is for this game. */
export function savedSessionFor(code: string): SavedSession | null {
  const raw = sessionStorage.getItem(KEY)
  if (!raw) {
    return null
  }
  try {
    const session = JSON.parse(raw) as SavedSession
    return session.code === code ? session : null
  } catch {
    return null
  }
}

export function forgetSession(): void {
  sessionStorage.removeItem(KEY)
}
