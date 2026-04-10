"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-24 text-center">
      <div className="border-t border-rule mb-6" />
      <h1 className="font-masthead text-4xl md:text-5xl text-ink font-black">
        Something Went Wrong
      </h1>
      <p className="text-ink-light mt-4 font-body max-w-md mx-auto">
        We couldn&apos;t load this edition. The presses may be down&mdash;please
        try again shortly.
      </p>
      {error.digest && (
        <p className="text-xs text-rule-dark mt-2 font-mono">
          Ref: {error.digest}
        </p>
      )}
      <button
        onClick={reset}
        className="mt-8 px-6 py-2.5 text-sm font-body font-semibold uppercase tracking-wider border-2 border-ink text-ink hover:bg-ink hover:text-paper transition-colors duration-200 cursor-pointer"
      >
        Try Again
      </button>
      <div className="border-t border-rule mt-6" />
    </div>
  );
}
