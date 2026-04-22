// Server-side proxy to /api/admin/* — injects the shared Bearer token so the
// browser bundle never sees it. Config:
//   ADMIN_API_TOKEN   (required) — matches backend ADMIN_TOKEN
//   BACKEND_API_URL   (required) — e.g. http://localhost:8000

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function forward(request: Request, context: RouteContext): Promise<Response> {
  const token = process.env.ADMIN_API_TOKEN;
  const backend = process.env.BACKEND_API_URL;

  if (!token || !backend) {
    return new Response(
      JSON.stringify({
        detail: "Admin proxy misconfigured: ADMIN_API_TOKEN and BACKEND_API_URL must be set",
      }),
      { status: 500, headers: { "content-type": "application/json" } },
    );
  }

  const { path } = await context.params;
  const incoming = new URL(request.url);
  const target = `${backend.replace(/\/$/, "")}/api/admin/${path.map(encodeURIComponent).join("/")}${incoming.search}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  headers.set("authorization", `Bearer ${token}`);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  const upstreamContentType = upstream.headers.get("content-type");
  if (upstreamContentType) responseHeaders.set("content-type", upstreamContentType);

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export async function GET(request: Request, context: RouteContext) {
  return forward(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return forward(request, context);
}
