import { useEffect, useState } from 'react';
import { Notice } from '../components/Notice';
import { FixtureViewer } from '../features/FixtureViewer';
import { Workspace } from '../features/documents/Workspace';
import { getJson } from '../lib/api';
import type { Capabilities } from '../lib/api';

export function App() {
  const [page, setPage] = useState<'intro' | 'demo' | 'workspace'>('intro');
  const [unsaved, setUnsaved] = useState(false);
  const [navigationError, setNavigationError] = useState('');
  function navigate(next: 'intro' | 'demo' | 'workspace') {
    if (unsaved && next !== page) {
      setNavigationError('Hãy lưu nháp hoặc bỏ chỉnh sửa trước khi chuyển trang.');
      return;
    }
    setNavigationError('');
    setPage(next);
  }
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
        <a
          href="#"
          className="brand"
          onClick={(event) => {
            event.preventDefault();
            navigate('intro');
          }}
        >
          <span className="brand-mark">D</span>
          <span>
            Document Intelligence<small>AI-02 · Biểu mẫu tiếng Việt</small>
          </span>
        </a>
        <nav aria-label="Điều hướng chính">
          <button
            aria-current={page === 'intro' ? 'page' : undefined}
            onClick={() => navigate('intro')}
          >
            Giới thiệu
          </button>
          <button
            aria-current={page === 'workspace' ? 'page' : undefined}
            onClick={() => navigate('workspace')}
          >
            Xử lý tài liệu
          </button>
          <button
            aria-current={page === 'demo' ? 'page' : undefined}
            onClick={() => navigate('demo')}
          >
            Mẫu minh họa
          </button>
        </nav>
        <span className="pill">LOCAL · 0.2.0</span>
      </header>
      <main>
        {navigationError && (
          <div role="alert" className="notice">
            {navigationError}
          </div>
        )}
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
                  Trích xuất dữ liệu từ hóa đơn và đơn đề nghị tiếng Việt. Đối chiếu ảnh nguồn, sửa
                  và lưu bản nháp, xác nhận trước khi xuất JSON.
                </p>
                <button className="primary" onClick={() => navigate('workspace')}>
                  Bắt đầu xử lý tài liệu <span aria-hidden="true">↗</span>
                </button>
                <p className="subtle">Chỉ sử dụng dữ liệu synthetic/sample có nguồn gốc rõ.</p>
              </div>
              <div className="hero-card">
                <span className="pill soft">OCR · ĐỐI CHIẾU · KIỂM SOÁT</span>
                <div className="paper-icon" aria-hidden="true">
                  <div />
                  <div />
                  <div />
                </div>
                <h2>Tài liệu của bạn, bản lưu của bạn.</h2>
                <p>Hóa đơn 5 trường · đơn đề nghị 7 trường · một trang</p>
                <div className="card-footer">Giữ prediction máy riêng với bản đã sửa.</div>
              </div>
            </section>
            <section className="section">
              <div className="section-heading">
                <h2>Trạng thái hiện tại</h2>
                <span className="subtle">Ứng dụng local · chỉ dùng synthetic/sample</span>
              </div>
              <div className="status-grid">
                <article>
                  <span className="status-dot green" /> <h3>Đang chạy</h3>
                  <p>
                    Upload, OCR Tesseract, evidence, lưu SQLite, review, xác nhận và export từ máy
                    chủ.
                  </p>
                </article>
                <article>
                  <span className="status-dot amber" /> <h3>Mẫu minh họa</h3>
                  <p>Ảnh synthetic và dự đoán viết sẵn để kiểm tra UI, hợp đồng và evaluator.</p>
                </article>
                <article>
                  <span className="status-dot gray" /> <h3>Phạm vi có giới hạn</h3>
                  <p>
                    Ảnh đánh máy một trang. Chưa hỗ trợ PDF, chữ viết tay, tài khoản hoặc triển khai
                    công khai.
                  </p>
                </article>
              </div>
            </section>
            <section className="section journey">
              <h2>Mỗi bước đều có thể kiểm tra</h2>
              <ol>
                <li>Tải tài liệu</li>
                <li>OCR & ánh xạ</li>
                <li>Đối chiếu & sửa</li>
                <li>Xác nhận & xuất</li>
              </ol>
              <p className="subtle">
                Confidence là heuristic chưa hiệu chỉnh. Người dùng đối chiếu tài liệu nguồn;
                validation hợp lệ chưa chứng minh dữ liệu khớp ảnh.
              </p>
            </section>
          </>
        ) : page === 'workspace' ? (
          <Workspace capabilities={capabilities} onUnsavedChange={setUnsaved} />
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
          OCR thật: {capabilities?.ocr_ready ? 'sẵn sàng' : 'chưa sẵn sàng'} · Confidence chưa hiệu
          chỉnh
          {capabilities ? ` · Provider: ${capabilities.provider_mode}` : ''}
        </span>
      </footer>
    </div>
  );
}
