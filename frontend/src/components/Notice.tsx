export function Notice({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="notice" role="alert">
      <p>{message}</p>
      {retry && <button onClick={retry}>Thử lại</button>}
    </div>
  );
}
