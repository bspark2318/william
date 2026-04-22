// HTTP Basic Auth on the admin surface. Protects both the UI route
// (/devs/admin/*) and the server-side proxy that forwards to the backend
// (/api/admin-proxy/*). Fails closed if ADMIN_UI_USER or ADMIN_UI_PASSWORD
// is unset — prevents accidentally shipping an open admin surface.
//
// Runs on the Edge runtime; uses crypto.subtle for a timing-safe compare
// that also normalizes length (hashing both sides before XOR).

import { NextRequest, NextResponse } from "next/server";

export const config = {
  matcher: ["/devs/admin/:path*", "/api/admin-proxy/:path*"],
};

const REALM = "devs-admin";

export async function proxy(request: NextRequest) {
  const user = process.env.ADMIN_UI_USER;
  const pass = process.env.ADMIN_UI_PASSWORD;

  if (!user || !pass) {
    return new NextResponse(
      JSON.stringify({ detail: "Admin UI auth not configured" }),
      { status: 503, headers: { "content-type": "application/json" } },
    );
  }

  const header = request.headers.get("authorization");
  if (!header || !header.toLowerCase().startsWith("basic ")) {
    return unauthorized();
  }

  let decoded: string;
  try {
    decoded = atob(header.slice("basic ".length).trim());
  } catch {
    return unauthorized();
  }

  const sep = decoded.indexOf(":");
  if (sep < 0) return unauthorized();
  const inUser = decoded.slice(0, sep);
  const inPass = decoded.slice(sep + 1);

  const [userOk, passOk] = await Promise.all([
    timingSafeEqual(inUser, user),
    timingSafeEqual(inPass, pass),
  ]);
  if (!userOk || !passOk) return unauthorized();

  return NextResponse.next();
}

function unauthorized() {
  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`,
      "content-type": "text/plain",
    },
  });
}

// Hashes both inputs before XOR so runtime doesn't depend on input length.
async function timingSafeEqual(a: string, b: string): Promise<boolean> {
  const enc = new TextEncoder();
  const [ha, hb] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(a)),
    crypto.subtle.digest("SHA-256", enc.encode(b)),
  ]);
  const av = new Uint8Array(ha);
  const bv = new Uint8Array(hb);
  let diff = 0;
  for (let i = 0; i < av.length; i++) diff |= av[i] ^ bv[i];
  return diff === 0;
}
