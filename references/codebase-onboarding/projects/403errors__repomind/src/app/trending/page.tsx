import { Suspense } from 'react';
import { Metadata } from 'next';
import { getCuratedRepos } from '@/lib/repo-catalog';
import TrendingClient from '@/components/TrendingClient';
import { buildOgImageUrl, createSeoMetadata } from '@/lib/seo';

export const metadata: Metadata = createSeoMetadata({
  title: "Trending Repositories",
  description: "Explore this week's most trending GitHub repositories. Analyze them instantly with RepoMind's AI-driven intelligence.",
  canonical: '/trending',
  keywords: ["trending github repos", "popular repositories", "github trends", "trending code", "repo analysis"],
  ogImage: buildOgImageUrl("marketing", { variant: "trending" }),
  ogTitle: "Trending GitHub repositories",
  ogDescription: "Explore the projects getting the most heat on GitHub this week.",
});

export default async function TrendingPage({
    searchParams
}: {
    searchParams: Promise<{ tier?: string }>
}) {
    const { tier: tierParam } = await searchParams;
    const tier = (tierParam as any) || 'weekly';
    const trendingRepos = await getCuratedRepos(tier);

    return (
        <Suspense fallback={null}>
            <TrendingClient initialRepos={trendingRepos} currentTier={tier} />
        </Suspense>
    );
}
