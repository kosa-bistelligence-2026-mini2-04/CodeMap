import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ owner: string; repo: string }>;
}): Promise<Metadata> {
  const { owner, repo } = await params;

  return {
    title: `Chat with ${owner}/${repo}`,
    description: `Use AI to chat with the codebase of ${owner}/${repo} in your browser.`,
  };
}

export default function RepoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
