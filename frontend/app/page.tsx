import type { Metadata } from "next";
import NewsletterLayout from "@/components/NewsletterLayout";
import { getIssue, getIssues } from "@/lib/api";
import { MOCK_ISSUE, MOCK_ISSUES } from "@/lib/mock-data";
import { Issue, IssueListItem } from "@/lib/types";

interface PageProps {
  searchParams: Promise<{ issue?: string }>;
}

async function fetchData(
  issueId?: string
): Promise<{ issue: Issue; allIssues: IssueListItem[] } | null> {
  try {
    const allIssues = await getIssues();
    if (!allIssues.length) return null;
    const targetId = issueId ? parseInt(issueId, 10) : allIssues[0]?.id;
    if (!targetId) return null;
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
    const data = await fetchData(params.issue);
    if (!data) {
      return {
        title: "The Context Window — Weekly AI Newsletter",
        description: "All the artificial intelligence news that's fit to print",
      };
    }
    const { issue } = data;
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
  const data = await fetchData(params.issue);

  if (!data) {
    return (
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-24 text-center">
        <div className="border-t border-rule mb-6" />
        <h1 className="font-masthead text-4xl md:text-5xl text-ink font-black">
          The Context Window
        </h1>
        <p className="text-ink-light mt-4 font-body max-w-md mx-auto">
          The first edition is on its way&mdash;check back soon.
        </p>
        <div className="border-t border-rule mt-6" />
      </div>
    );
  }

  const { issue, allIssues } = data;
  return (
    <NewsletterLayout
      issue={issue}
      allIssueIds={allIssues.map((i) => ({ id: i.id, week_of: i.week_of }))}
    />
  );
}
