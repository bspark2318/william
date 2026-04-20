export default function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="border border-red-500/50 bg-red-500/10 text-red-300 px-4 py-3 rounded text-xs font-mono whitespace-pre-wrap break-words"
    >
      <span className="uppercase tracking-widest mr-2">error:</span>
      {message}
    </div>
  );
}
