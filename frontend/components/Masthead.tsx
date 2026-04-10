interface MastheadProps {
  title?: string;
  weekOf: string;
  issueNumber?: number;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function Masthead({ title, weekOf, issueNumber }: MastheadProps) {
  return (
    <header className="text-center pt-6 pb-4 border-b-2 border-ink mb-4">
      {/* Top thin rule + date line */}
      <div className="border-t border-rule mb-3" />
      <div className="flex items-center justify-between text-[11px] text-ink-light uppercase tracking-wider font-body max-w-4xl mx-auto mb-3">
        <span>{formatDate(weekOf)}</span>
        <span>Weekly Edition</span>
        {issueNumber != null && <span>No. {issueNumber}</span>}
      </div>
      <div className="border-t border-rule mb-4" />

      {/* Masthead title */}
      <h1 className="font-masthead text-5xl md:text-7xl text-ink tracking-tight leading-none font-black">
        The AI Prophet
      </h1>

      {/* Tagline */}
      <p className="text-xs md:text-sm text-ink-light mt-3 tracking-[0.2em] uppercase font-body">
        All the Artificial Intelligence News That&apos;s Fit to Print
      </p>

      {/* Issue title */}
      {title && (
        <>
          <div className="border-t border-rule max-w-xs mx-auto mt-4 mb-3" />
          <h2 className="font-headline text-xl md:text-2xl text-ink mt-1 font-bold italic">
            {title}
          </h2>
        </>
      )}
    </header>
  );
}
