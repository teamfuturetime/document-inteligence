import { Link, Route, Routes } from "react-router-dom";

function Home() { return <main className="mx-auto max-w-5xl p-8"><h1 className="text-4xl font-bold">Hiểu biểu mẫu Việt</h1><p className="mt-3 text-lg">Số hóa biểu mẫu, kiểm tra và xác nhận chỉ trong vài bước.</p></main>; }

export default function App() {
  return <><header className="border-b bg-white"><nav className="mx-auto flex max-w-5xl gap-6 p-4"><Link className="font-bold text-brand" to="/">Document AI</Link><Link to="/upload">Tải tài liệu</Link><Link to="/documents">Lịch sử</Link></nav></header><Routes><Route path="*" element={<Home />} /></Routes></>;
}
