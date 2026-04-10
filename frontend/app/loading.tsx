export default function Loading() {
  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 pb-16 animate-pulse">
      {/* Masthead skeleton */}
      <header className="text-center pt-6 pb-4 border-b-2 border-rule mb-4">
        <div className="border-t border-rule mb-3" />
        <div className="flex items-center justify-between max-w-4xl mx-auto mb-3">
          <div className="h-3 w-40 bg-rule rounded" />
          <div className="h-3 w-24 bg-rule rounded" />
          <div className="h-3 w-12 bg-rule rounded" />
        </div>
        <div className="border-t border-rule mb-4" />
        <div className="h-12 md:h-16 w-3/4 bg-rule rounded mx-auto" />
        <div className="h-3 w-64 bg-rule rounded mx-auto mt-4" />
      </header>

      {/* Two-column skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_300px] gap-8 mt-6">
        <main className="space-y-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex gap-5 py-4">
              <div className="hidden sm:block shrink-0 w-28 h-28 bg-rule rounded" />
              <div className="flex-1 space-y-2">
                <div className="h-3 w-32 bg-rule rounded" />
                <div className="h-5 w-3/4 bg-rule rounded" />
                <div className="h-3 w-full bg-rule rounded" />
                <div className="h-3 w-5/6 bg-rule rounded" />
              </div>
            </div>
          ))}
        </main>

        <aside className="space-y-6">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="border border-rule overflow-hidden">
              <div className="aspect-video bg-rule" />
              <div className="p-3 bg-paper-alt space-y-2">
                <div className="h-4 w-3/4 bg-rule rounded" />
                <div className="h-3 w-full bg-rule rounded" />
              </div>
            </div>
          ))}
        </aside>
      </div>
    </div>
  );
}
