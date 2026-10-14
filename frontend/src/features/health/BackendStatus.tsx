import { useEffect, useRef, useState } from 'react'
import { getHealth } from '../../api/client'
import type { HealthResponse } from '../../api/generated/health-response'

type Connection =
  | { status: 'idle' | 'loading' }
  | { status: 'connected'; data: HealthResponse }
  | { status: 'error'; message: string }

export function BackendStatus() {
  const [connection, setConnection] = useState<Connection>({ status: 'idle' })
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => { request.current?.abort() }, [])

  async function checkConnection() {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setConnection({ status: 'loading' })
    try {
      const data = await getHealth(controller.signal)
      if (!controller.signal.aborted) setConnection({ status: 'connected', data })
    } catch (error) {
      if (!controller.signal.aborted) {
        setConnection({ status: 'error', message: error instanceof Error ? error.message : 'Không thể kết nối backend.' })
      }
    }
  }

  return (
    <section className="panel" aria-labelledby="connection-heading">
      <span className="step">02 / KẾT NỐI</span>
      <h2 id="connection-heading">Kiểm tra backend</h2>
      <p>Kết nối dịch vụ trước khi tích hợp luồng xử lý tài liệu.</p>
      <button onClick={checkConnection} disabled={connection.status === 'loading'}>
        {connection.status === 'loading' ? 'Đang kiểm tra…' : 'Kiểm tra kết nối'}
      </button>
      <div aria-live="polite" aria-busy={connection.status === 'loading'} className="connection-result">
        {connection.status === 'idle' ? <p className="empty">Chưa kiểm tra kết nối.</p> : null}
        {connection.status === 'connected' ? (
          <>
            <p className="success">Backend đang hoạt động.</p>
            <dl>
              <div><dt>Chế độ</dt><dd>{connection.data.mode === 'mock' ? 'Mock' : 'Real'}</dd></div>
              <div><dt>OCR</dt><dd>{connection.data.ocr_ready ? 'Sẵn sàng' : 'Chưa sẵn sàng'}</dd></div>
            </dl>
            <p className="note">Kết nối thành công chỉ xác nhận dịch vụ đang chạy.</p>
          </>
        ) : null}
        {connection.status === 'error' ? <p role="alert" className="error">{connection.message}</p> : null}
      </div>
    </section>
  )
}
