import type { Metadata } from "next";
import Link from "next/link";
import { buildOgImageUrl, createSeoMetadata, truncateMetaText } from "@/lib/seo";

function formatFeatureLabel(raw?: string): string {
  if (!raw) return "This feature";
  return raw
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ feature?: string; slug?: string }>;
}): Promise<Metadata> {
  const { feature, slug } = await searchParams;
  const label = formatFeatureLabel(feature ?? slug);
  const title = label === "This feature" ? "Coming Soon" : `${label} Coming Soon`;
  const description = truncateMetaText(
    label === "This feature"
      ? "This RepoMind page is under active development and will be available soon."
      : `${label} is on the roadmap. RepoMind is actively building this experience.`,
    180,
  );

  return createSeoMetadata({
    title,
    description,
    canonical: feature
      ? `/coming-soon?feature=${encodeURIComponent(feature)}`
      : slug
        ? `/coming-soon?slug=${encodeURIComponent(slug)}`
        : "/coming-soon",
    ogImage: buildOgImageUrl("marketing", {
      variant: "coming-soon",
      title,
      description,
      footer: "Roadmap",
    }),
    ogTitle: title,
    ogDescription: description,
    noIndex: true,
  });
}

export default async function ComingSoonPage({
  searchParams,
}: {
  searchParams: Promise<{ feature?: string; slug?: string }>;
}) {
  const { feature, slug } = await searchParams;
  const label = formatFeatureLabel(feature ?? slug);

  return (
    <main className="min-h-screen bg-[#09090b] text-white px-6 py-24">
      <div className="mx-auto max-w-3xl rounded-3xl border border-white/10 bg-zinc-900/40 p-8 md:p-10 text-center">
        <p className="text-cyan-300 text-xs uppercase tracking-[0.22em] mb-4">Coming Soon</p>
        <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-5">{label} is on the roadmap</h1>
        <p className="text-zinc-300 leading-relaxed mb-8">
          We are actively building this page. You can explore current capabilities from Solutions and Insights meanwhile.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/solutions" className="px-5 py-3 rounded-xl bg-white text-black font-medium hover:bg-zinc-200 transition-colors">
            Explore Solutions
          </Link>
          <Link href="/blog" className="px-5 py-3 rounded-xl border border-white/15 text-zinc-200 hover:bg-zinc-800/60 transition-colors">
            Read Insights
          </Link>
        </div>
      </div>
    </main>
  );
}
