import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import UploadPage from './UploadPage'

const mocks = vi.hoisted(() => ({ upload: vi.fn(), process: vi.fn() }))
vi.mock('../api/client', () => ({ api: mocks }))
function view() {
  return render(<MemoryRouter><Routes><Route path="/" element={<UploadPage />} />
    <Route path="/documents/doc" element={<p>Chi tiết tài liệu</p>} /></Routes></MemoryRouter>)
}
beforeEach(() => { mocks.upload.mockReset().mockResolvedValue({ id: 'doc' }); mocks.process.mockReset().mockResolvedValue({}) })
afterEach(cleanup)

describe('UploadPage extended formats', () => {
  it('selects TIFF, keeps loading state, processes and navigates to detail', async () => {
    const { container } = view()
    expect(screen.getByText('Hỗ trợ PDF, PNG, JPG, JPEG, WebP, BMP và TIFF, tối đa 10 MB.')).toBeInTheDocument()
    const input = container.querySelector('input[type="file"]')!
    expect(input).toHaveAttribute('accept', '.pdf,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff')
    const file = new File(['tiff'], 'scan.tiff', { type: 'image/tiff' })
    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: 'Tải lên và xử lý' }))
    expect(screen.getByRole('button', { name: /AI đang xử lý/ })).toBeDisabled()
    expect(await screen.findByText('Chi tiết tài liệu')).toBeInTheDocument()
    expect(mocks.upload).toHaveBeenCalledWith(file)
    expect(mocks.process).toHaveBeenCalledWith('doc')
  })

  it.each([['scan.webp', 'image/webp'], ['scan.bmp', 'image/bmp'], ['scan.tif', '']])('accepts dropped %s', (name, type) => {
    const { container } = view()
    fireEvent.drop(container.querySelector('label')!, { dataTransfer: { files: [new File(['image'], name, { type })] } })
    expect(screen.getByText(name)).toBeInTheDocument()
  })

  it('keeps the failure message and re-enables submit', async () => {
    mocks.process.mockRejectedValue(new Error('OCR thất bại'))
    const { container } = view()
    fireEvent.change(container.querySelector('input')!, { target: { files: [new File(['bmp'], 'scan.bmp', { type: 'image/bmp' })] } })
    fireEvent.click(screen.getByRole('button', { name: 'Tải lên và xử lý' }))
    expect(await screen.findByText('OCR thất bại')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Tải lên và xử lý' })).toBeEnabled())
  })
})
