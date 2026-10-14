import { BackendStatus } from './features/health/BackendStatus'
import { DocumentSelection } from './features/documents/DocumentSelection'

export default function App() {
  return (
    <div className="app-shell">
      <header className="masthead">
        <a className="brand" href="#main">VDI <span>/ AI-02</span></a>
        <span className="badge">Development · Phase 2</span>
      </header>
      <main id="main">
        <div className="intro">
          <p className="eyebrow">VIETNAMESE DOCUMENT INTELLIGENCE</p>
          <h1>Từ tài liệu đến<br />dữ liệu có cấu trúc.</h1>
          <p className="lead">Không gian làm việc cho hóa đơn tiếng Việt. Chuẩn bị mẫu và kiểm tra kết nối để bắt đầu.</p>
        </div>
        <div className="workspace"><DocumentSelection /><BackendStatus /></div>
        <aside className="scope" aria-label="Trạng thái triển khai">
          <strong>Đã có</strong><span>Upload với mock · Kiểm tra backend</span>
          <strong>Sắp triển khai</strong><span>OCR · Review · Xuất JSON</span>
        </aside>
      </main>
      <footer>Mẫu synthetic, không sử dụng thông tin cá nhân thật.</footer>
    </div>
  )
}
