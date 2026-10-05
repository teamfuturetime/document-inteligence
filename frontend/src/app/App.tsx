import { useEffect, useState } from 'react';
import { Notice } from '../components/Notice';
import { FixtureViewer } from '../features/FixtureViewer';
import { getJson } from '../lib/api';
import type { Capabilities } from '../lib/api';

export function App() {
  const [page, setPage] = useState<'intro' | 'demo'>('intro');
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    getJson<Capabilities>('/capabilities', controller.signal)
      .then(setCapabilities)
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, [attempt]);
  return (
    <div className="shell">
      <header className="topbar">
        <a href="#" className="brand" onClick={() => setPage('intro')}>
          <span className="brand-mark">D</span>
          <span>
            Document Intelligence<small>AI-02 · Biểu mẫu tiếng Việt</small>
          </span>
        </a>
        <nav aria-label="Điều hướng chính">
          <button
            aria-current={page === 'intro' ? 'page' : undefined}
            onClick={() => setPage('intro')}
          >
            Giới thiệu
          </button>
          <button
            aria-current={page === 'demo' ? 'page' : undefined}
            onClick={() => setPage('demo')}
          >
            Mẫu minh họa
          </button>
        </nav>
        <span className="pill">FOUNDATION 0.1.0</span>
      </header>
      <main>
        {error && (
          <Notice
            message={`Không kết nối được backend: ${error}`}
            retry={() => setAttempt(attempt + 1)}
          />
        )}
        {!capabilities && !error && <p role="status">Đang kiểm tra khả năng backend…</p>}
        {page === 'intro' ? (
          <>
            <section className="hero">
              <div>
                <p className="eyebrow">ĐỌC TÀI LIỆU. GIỮ QUYỀN KIỂM SOÁT.</p>
                <h1>
                  Từ biểu mẫu
                  <br />
                  đến dữ liệu có cấu trúc.
                </h1>
                <p className="lead">
                  Nền tảng dự án trích xuất trường dữ liệu tiếng Việt, giúp người dùng đối chiếu và
                  sửa trước khi xuất JSON.
                </p>
                <button className="primary" onClick={() => setPage('demo')}>
                  Khám phá mẫu minh họa <span aria-hidden="true">↗</span>
                </button>
                <p className="subtle">Chỉ sử dụng dữ liệu synthetic/sample có nguồn gốc rõ.</p>
              </div>
              <div className="hero-card">
                <span className="pill soft">HỢP ĐỒNG MẪU · PROVISIONAL</span>
                <div className="paper-icon" aria-hidden="true">
                  <div />
                  <div />
                  <div />
                </div>
                <h2>Đơn đề nghị</h2>
                <p>7 trường · một trang · tiếng Việt đánh máy</p>
                <div className="card-footer">Mẫu giả lập — chưa chạy OCR</div>
              </div>
            </section>
            <section className="section">
              <div className="section-heading">
                <h2>Trạng thái hiện tại</h2>
                <span className="subtle">Foundation chưa phải MVP</span>
              </div>
              <div className="status-grid">
                <article>
                  <span className="status-dot green" /> <h3>Đang chạy</h3>
                  <p>API nền, contracts, chuẩn hóa, validation và bộ chấm điểm trên fixture.</p>
                </article>
                <article>
                  <span className="status-dot amber" /> <h3>Mẫu minh họa</h3>
                  <p>Ảnh synthetic và dự đoán viết sẵn để kiểm tra UI, hợp đồng và evaluator.</p>
                </article>
                <article>
                  <span className="status-dot gray" /> <h3>Chưa triển khai</h3>
                  <p>Upload, OCR thật, extraction thật, lưu revision, xác nhận và export.</p>
                </article>
              </div>
            </section>
            <section className="section journey">
              <h2>Quy trình sản phẩm đích</h2>
              <ol>
                <li>Tải tài liệu</li>
                <li>OCR & ánh xạ</li>
                <li>Đối chiếu & sửa</li>
                <li>Xác nhận & xuất</li>
              </ol>
              <p className="subtle">
                Đây là thiết kế mục tiêu. Confidence chưa được hiệu chỉnh; chất lượng mô hình chưa
                đo.
              </p>
            </section>
          </>
        ) : (
          <section className="section demo-section">
            <p className="eyebrow">PHÒNG MẪU</p>
            <h1>Đối chiếu theo từng trường</h1>
            <p className="lead">
              Xem hợp đồng dữ liệu và các tình huống cần kiểm tra trước khi xây luồng review đầy đủ.
            </p>
            {capabilities ? (
              <FixtureViewer mode={capabilities.provider_mode} />
            ) : (
              <p>Đang chờ khả năng backend.</p>
            )}
          </section>
        )}
      </main>
      <footer>
        <span>AI-02 · Document Intelligence</span>
        <span>
          OCR thật: chưa triển khai · Chất lượng mô hình: chưa đo
          {capabilities ? ` · Provider: ${capabilities.provider_mode}` : ''}
        </span>
      </footer>
    </div>
  );
}
