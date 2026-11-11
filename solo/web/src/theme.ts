export type Theme = 'light' | 'dark'

// Keep this key and the startup colors in sync with the pre-paint script in index.html.
export const THEME_STORAGE_KEY = 'ai02-solo-theme-v1'

export function parseTheme(value: string | null): Theme | null {
  return value === 'light' || value === 'dark' ? value : null
}

export function readThemePreference(): Theme | null {
  try { return parseTheme(window.localStorage.getItem(THEME_STORAGE_KEY)) }
  catch { return null }
}

export function systemTheme(): Theme {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'light' ? '#f3f5ef' : '#161c1a')
}
