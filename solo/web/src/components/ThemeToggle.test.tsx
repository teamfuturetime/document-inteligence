import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import ThemeToggle from './ThemeToggle'
import { THEME_STORAGE_KEY } from '../theme'

let light: boolean
let media: EventTarget

beforeEach(() => {
  localStorage.clear()
  light = true
  media = new EventTarget()
  vi.stubGlobal('matchMedia', () => ({
    matches: light,
    addEventListener: media.addEventListener.bind(media),
    removeEventListener: media.removeEventListener.bind(media),
  }))
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); delete document.documentElement.dataset.theme })

test('uses system appearance until a choice is made, then remembers the explicit choice', () => {
  render(<ThemeToggle />)
  expect(document.documentElement.dataset.theme).toBe('light')
  light = false
  act(() => { media.dispatchEvent(new Event('change')) })
  expect(document.documentElement.dataset.theme).toBe('dark')
  fireEvent.click(screen.getByRole('button', { name: 'Chuyển sang chế độ sáng' }))
  expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light')
  act(() => { media.dispatchEvent(new Event('change')) })
  expect(document.documentElement.dataset.theme).toBe('light')
  cleanup()
  render(<ThemeToggle />)
  expect(document.documentElement.dataset.theme).toBe('light')
})

test('ignores invalid saved values and synchronizes a changed or cleared preference from another tab', () => {
  localStorage.setItem(THEME_STORAGE_KEY, 'invalid')
  render(<ThemeToggle />)
  expect(document.documentElement.dataset.theme).toBe('light')
  fireEvent(window, new StorageEvent('storage', { key: THEME_STORAGE_KEY, newValue: 'dark' }))
  expect(document.documentElement.dataset.theme).toBe('dark')
  fireEvent(window, new StorageEvent('storage', { key: null, newValue: null }))
  expect(document.documentElement.dataset.theme).toBe('light')
})

test('still switches appearance when browser storage is unavailable', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked') })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked') })
  render(<ThemeToggle />)
  fireEvent.click(screen.getByRole('button', { name: 'Chuyển sang chế độ tối' }))
  expect(document.documentElement.dataset.theme).toBe('dark')
  expect(document.documentElement.style.colorScheme).toBe('dark')
})
