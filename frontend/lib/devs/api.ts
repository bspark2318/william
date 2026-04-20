import { DevPost } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getDevPosts(): Promise<DevPost[]> {
  const res = await fetch(`${API_URL}/api/devs/posts`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`Failed to fetch dev posts: ${res.status}`);
  return res.json();
}
