import { useEffect, useLayoutEffect, useState } from 'react'
import { applyTheme, parseTheme, readThemePreference, systemTheme, THEME_STORAGE_KEY } from '../theme'
import type { Theme } from '../theme'
import Icon from './Icon'

export default function ThemeToggle() {
  const [preference, setPreference] = useState<Theme | null>(readThemePreference)
  const [system, setSystem] = useState<Theme>(systemTheme)
  const theme = preference ?? system
  const next = theme === 'dark' ? 'light' : 'dark'
  const label = `Chuyển sang chế độ ${next === 'light' ? 'sáng' : 'tối'}`

  useLayoutEffect(() => { applyTheme(theme) }, [theme])

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: light)')
    const onSystemChange = () => setSystem(systemTheme())
    const onStorage = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY || event.key === null) setPreference(parseTheme(event.newValue))
    }
    media?.addEventListener('change', onSystemChange)
    window.addEventListener('storage', onStorage)
    return () => {
      media?.removeEventListener('change', onSystemChange)
      window.removeEventListener('storage', onStorage)
    }
  }, [])

  function toggle() {
    setPreference(next)
    try { window.localStorage.setItem(THEME_STORAGE_KEY, next) }
    catch { /* The selected theme still works for this session when storage is blocked. */ }
  }

  return <button className="theme-toggle" aria-label={label} title={label} onClick={toggle}>
    <Icon name={next === 'light' ? 'sun' : 'moon'} /><span>{next === 'light' ? 'Sáng' : 'Tối'}</span>
  </button>
}
