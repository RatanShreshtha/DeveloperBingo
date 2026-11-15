// The light or dark theme. A visitor's choice is kept in this browser; until they choose, the
// operating system's preference decides. The choice is written to the page's `data-theme`, which
// daisyUI and the `dark:` variant both read, so the page always shows one theme.

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'devbingo-theme'

function storedTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    // Storage can be blocked, such as in some private windows: fall back to the system.
    return null
  }
}

function systemTheme(): Theme {
  const dark =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  return dark ? 'dark' : 'light'
}

/** The theme in effect: the visitor's choice, or else the operating system's. */
export function currentTheme(): Theme {
  return storedTheme() ?? systemTheme()
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
}

/** Makes the theme the visitor's choice, saves it, and applies it. */
export function setTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Not saved: the theme still applies for this visit.
  }
  applyTheme(theme)
}
