import NewsletterLayout from "@/components/NewsletterLayout";
import { getIssue, getIssues } from "@/lib/api";
import { MOCK_ISSUE, MOCK_ISSUES } from "@/lib/mock-data";
import { Issue, IssueListItem } from "@/lib/types";

interface PageProps {
  searchParams: Promise<{ issue?: string }>;
}

async function fetchData(issueId?: string): Promise<{ issue: Issue; allIssues: IssueListItem[] }> {
  try {
    const allIssues = await getIssues();
    const targetId = issueId ? parseInt(issueId, 10) : allIssues[0]?.id;
    if (!targetId) throw new Error("No issues available");
    const issue = await getIssue(targetId);
    return { issue, allIssues };
  } catch {
    return { issue: MOCK_ISSUE, allIssues: MOCK_ISSUES };
  }
}

export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const { issue, allIssues } = await fetchData(params.issue);

  return (
    <NewsletterLayout
      issue={issue}
      allIssueIds={allIssues.map((i) => ({ id: i.id, week_of: i.week_of }))}
    />
  );
}
