export default function App() {
  return (
    <main className="workspace">
      <header className="masthead">
        <span className="brand-mark" aria-hidden="true">AI·02</span>
        <span>Biểu mẫu tiếng Việt</span>
      </header>

      <section className="introduction" aria-labelledby="project-title">
        <p className="eyebrow">Từ tài liệu đến dữ liệu</p>
        <h1 id="project-title">AI-02 — Document Intelligence</h1>
        <p className="description">
          Trích xuất dữ liệu từ hóa đơn và biểu mẫu tiếng Việt, kiểm tra và
          chỉnh sửa từng trường, sau đó xuất kết quả thành JSON.
        </p>
      </section>

      <section className="status-panel" aria-labelledby="status-title">
        <div className="status-heading">
          <h2 id="status-title">Trạng thái dự án</h2>
          <span className="phase">Giai đoạn 1 · Đang phát triển</span>
        </div>
        <p>
          Giao diện ban đầu đã sẵn sàng. Các chức năng xử lý tài liệu sẽ được
          bổ sung theo từng giai đoạn.
        </p>
        <dl className="milestones">
          <div>
            <dt>Giao diện giới thiệu</dt>
            <dd className="available">Đã có</dd>
          </div>
          <div>
            <dt>Nhận dạng và trích xuất</dt>
            <dd>Chưa triển khai</dd>
          </div>
          <div>
            <dt>Kiểm tra, chỉnh sửa và xuất JSON</dt>
            <dd>Chưa triển khai</dd>
          </div>
        </dl>
      </section>

      <footer>Chỉ sử dụng tài liệu tổng hợp hoặc dữ liệu mẫu được phép sử dụng.</footer>
    </main>
  )
}
