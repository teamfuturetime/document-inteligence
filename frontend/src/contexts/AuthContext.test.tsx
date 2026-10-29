import {useState} from 'react'
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import '@testing-library/jest-dom/vitest'
import {AuthProvider, useAuth} from './AuthContext'

const mocks = vi.hoisted(() => ({me: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn()}))
vi.mock('../api/client', () => ({api: mocks}))
const user = {id: 'owner', username: 'reviewer', email: 'owner@example.test', created_at: '2026-01-01'}
function Controls() {
  const {user, logout, login} = useAuth()
  const [error, setError] = useState('')
  return <><span>{user?.username || 'Logged out'}</span><button onClick={() => void logout().catch(e => setError(e.message))}>Logout</button><button onClick={() => void login('other', 'test-password')}>Login other</button>{error && <p role="alert">{error}</p>}</>
}
async function view() {
  render(<AuthProvider><Controls/></AuthProvider>)
  await screen.findByText('reviewer')
  sessionStorage.setItem('vt043:ocr-draft:doc', JSON.stringify({text: 'Bản nháp', expected_revision: 0}))
}

describe('OCR draft privacy during authentication changes', () => {
  beforeEach(() => {sessionStorage.clear(); vi.resetAllMocks(); mocks.me.mockResolvedValue(user); mocks.logout.mockResolvedValue(undefined)})
  afterEach(() => {cleanup(); vi.restoreAllMocks()})

  it('allows cancelling logout to keep unsaved draft text', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false); await view()
    fireEvent.click(screen.getByRole('button', {name: 'Logout'}))
    expect(window.confirm).toHaveBeenCalled()
    expect(mocks.logout).not.toHaveBeenCalled()
    expect(sessionStorage.getItem('vt043:ocr-draft:doc')).not.toBeNull()
    expect(screen.getByText('reviewer')).toBeInTheDocument()
  })

  it('clears only OCR draft entries after successful logout', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true); await view()
    sessionStorage.setItem('unrelated', 'keep')
    fireEvent.click(screen.getByRole('button', {name: 'Logout'}))
    await screen.findByText('Logged out')
    expect(sessionStorage.getItem('vt043:ocr-draft:doc')).toBeNull()
    expect(sessionStorage.getItem('unrelated')).toBe('keep')
  })

  it('keeps authenticated drafts if logout fails', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true); mocks.logout.mockRejectedValue(new Error('Network offline')); await view()
    fireEvent.click(screen.getByRole('button', {name: 'Logout'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Network offline')
    expect(sessionStorage.getItem('vt043:ocr-draft:doc')).not.toBeNull()
    expect(screen.getByText('reviewer')).toBeInTheDocument()
  })

  it('clears previous account drafts when a different account signs in', async () => {
    await view(); mocks.login.mockResolvedValue({...user, id: 'other', username: 'other'})
    fireEvent.click(screen.getByRole('button', {name: 'Login other'}))
    await waitFor(() => expect(screen.getByText('other')).toBeInTheDocument())
    expect(sessionStorage.getItem('vt043:ocr-draft:doc')).toBeNull()
  })
})
