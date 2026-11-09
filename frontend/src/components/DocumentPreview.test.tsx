import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import DocumentPreview from './DocumentPreview'
import type { Document } from '../types'

const document = { id: 'doc', filename: 'scan.tiff', content_type: 'image/tiff' } as Document
vi.mock('../api/client', () => ({ api: { preview: (id: string) => '/preview/' + id } }))

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('DocumentPreview', () => {
  it('loads TIFF pages as PNG and revokes URLs', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response(new Blob(['png'], { type: 'image/png' }), {
      headers: { 'X-Page-Count': '2' },
    }))
    vi.stubGlobal('fetch', fetchMock)
    const create = vi.fn().mockReturnValueOnce('blob:page-1').mockReturnValueOnce('blob:page-2')
    const revoke = vi.fn()
    vi.stubGlobal('URL', { createObjectURL: create, revokeObjectURL: revoke })
    const view = render(<DocumentPreview document={document} />)
    expect(await screen.findByRole('img')).toHaveAttribute('src', 'blob:page-1')
    expect(screen.getByText('Trang 1 / 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Trang trước' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(screen.getByRole('img')).toHaveAttribute('src', 'blob:page-2'))
    expect(fetchMock).toHaveBeenLastCalledWith('/preview/doc?page=2', expect.objectContaining({ credentials: 'include' }))
    expect(screen.getByRole('button', { name: 'Trang sau' })).toBeDisabled()
    expect(revoke).toHaveBeenCalledWith('blob:page-1')
    view.unmount()
    expect(revoke).toHaveBeenCalledWith('blob:page-2')
  })

  it('reports a failed converted preview', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 422 })))
    render(<DocumentPreview document={{ ...document, filename: 'scan.bmp' }} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải bản xem trước')
  })

  it('keeps the existing PDF and image preview URLs', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const view = render(<DocumentPreview document={{ ...document, filename: 'scan.pdf', content_type: 'application/pdf' }} />)
    expect(screen.getByTitle('Xem PDF')).toHaveAttribute('src', '/preview/doc')
    view.rerender(<DocumentPreview document={{ ...document, filename: 'scan.webp', content_type: 'image/webp' }} />)
    expect(screen.getByRole('img')).toHaveAttribute('src', '/preview/doc')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
