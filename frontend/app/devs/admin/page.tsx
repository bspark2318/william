import type { Metadata } from "next";
import AdminConsole from "@/components/devs/admin/AdminConsole";

export const metadata: Metadata = {
  title: "The Context Window — /devs admin",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default function DevsAdminPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 md:px-8 py-10 md:py-12">
      <header className="mb-8">
        <h1 className="text-lg md:text-xl font-semibold text-[#d4d4d8]">
          <span className="text-[#7cffb2]">$</span> devs/admin
        </h1>
        <p className="text-xs text-[#71717a] mt-1 font-mono">
          skill-dev feed controls · not publicly linked · no auth yet
        </p>
      </header>
      <AdminConsole />
    </div>
  );
}
