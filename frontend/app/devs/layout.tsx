import { JetBrains_Mono } from "next/font/google";

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export default function DevsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`${jetbrainsMono.variable} flex-1 min-h-screen bg-[#0b0d10] text-[#d4d4d8]`}
      style={{ fontFamily: "var(--font-mono), ui-monospace, SFMono-Regular, Menlo, monospace" }}
    >
      {children}
    </div>
  );
}
