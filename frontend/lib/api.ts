import { Issue, IssueListItem } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getIssues(): Promise<IssueListItem[]> {
  const res = await fetch(`${API_URL}/api/issues`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`Failed to fetch issues: ${res.status}`);
  return res.json();
}

export async function getIssue(id: number): Promise<Issue> {
  const res = await fetch(`${API_URL}/api/issues/${id}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`Failed to fetch issue ${id}: ${res.status}`);
  return res.json();
}

export async function getLatestIssue(): Promise<Issue> {
  const issues = await getIssues();
  if (issues.length === 0) throw new Error("No issues found");
  return getIssue(issues[0].id);
}
