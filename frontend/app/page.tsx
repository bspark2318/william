import type { Metadata } from "next";
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
    if (process.env.NODE_ENV === "development") {
      return { issue: MOCK_ISSUE, allIssues: MOCK_ISSUES };
    }
    throw new Error("Unable to load newsletter data");
  }
}

export async function generateMetadata({ searchParams }: PageProps): Promise<Metadata> {
  try {
    const params = await searchParams;
    const { issue } = await fetchData(params.issue);
    return {
      title: `${issue.title} — The Context Window No. ${issue.edition}`,
      description: `Week of ${issue.week_of}: ${issue.stories.length} stories on AI research, policy, and industry.`,
    };
  } catch {
    return {
      title: "The Context Window — Weekly AI Newsletter",
      description: "All the artificial intelligence news that's fit to print",
    };
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
