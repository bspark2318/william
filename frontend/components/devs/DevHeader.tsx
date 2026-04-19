import Link from "next/link";

export default function DevHeader() {
  return (
    <header className="border-b border-[#1f2329] pb-6 mb-8">
      <div className="flex items-center gap-2 text-xs text-[#71717a]">
        <span className="text-[#7cffb2]">$</span>
        <span>cat /context-window/devs/signals.md</span>
      </div>

      <div className="mt-6 flex items-baseline gap-4">
        <span className="text-[#7cffb2] text-sm">#</span>
        <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
          For Developers
        </h1>
      </div>

      <p className="mt-2 text-sm text-[#a1a1aa] pl-6">
        Signals to level up as an AI-era engineer.
      </p>

      <div className="mt-4 pl-6">
        <Link
          href="/"
          className="text-xs text-[#71717a] hover:text-[#d4d4d8] transition-colors"
        >
          &larr; /
        </Link>
      </div>
    </header>
  );
}
