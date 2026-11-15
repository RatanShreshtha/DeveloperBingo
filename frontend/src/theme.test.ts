import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyTheme, currentTheme, setTheme } from './theme'

function systemPrefersDark(dark: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: dark }) as MediaQueryList),
  )
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  systemPrefersDark(false)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('theme', () => {
  it('follows the operating system when nothing has been chosen', () => {
    systemPrefersDark(true)

    expect(currentTheme()).toBe('dark')
  })

  it('keeps the theme the visitor chose, over the operating system', () => {
    systemPrefersDark(true)
    localStorage.setItem('devbingo-theme', 'light')

    expect(currentTheme()).toBe('light')
  })

  it('ignores a stored value that is not a theme', () => {
    localStorage.setItem('devbingo-theme', 'purple')

    expect(currentTheme()).toBe('light')
  })

  it('saves the chosen theme and applies it to the page', () => {
    setTheme('dark')

    expect(localStorage.getItem('devbingo-theme')).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(currentTheme()).toBe('dark')
  })

  it('applies the theme in effect when the app starts', () => {
    systemPrefersDark(true)

    applyTheme(currentTheme())

    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})
