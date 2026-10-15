import { BackendStatus } from './features/health/BackendStatus'
import { DocumentSelection } from './features/documents/DocumentSelection'

export default function App() {
  return (
    <div className="app-shell">
      <header className="masthead">
        <a className="brand" href="#main">VDI <span>/ AI-02</span></a>
        <span className="badge">Synthetic invoice workspace</span>
      </header>
      <main id="main">
        <div className="intro">
          <p className="eyebrow">VIETNAMESE DOCUMENT INTELLIGENCE</p>
          <h1>Từ tài liệu đến<br />dữ liệu có cấu trúc.</h1>
          <p className="lead">Upload hóa đơn tiếng Việt, đối chiếu kết quả OCR và xác nhận dữ liệu trước khi xuất.</p>
        </div>
        <div className="workspace"><DocumentSelection /><BackendStatus /></div>
        <aside className="scope" aria-label="Trạng thái triển khai">
          <strong>Luồng xử lý</strong><span>OCR · Review · Xuất JSON</span>
          <strong>Phạm vi</strong><span>Hóa đơn synthetic một trang · PNG/JPG/PDF</span>
        </aside>
      </main>
      <footer>Mẫu synthetic, không sử dụng thông tin cá nhân thật.</footer>
    </div>
  )
}
