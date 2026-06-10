import type { Metadata } from "next";
import Link from "next/link";
import JsonLdScript from "@/components/JsonLdScript";
import SeoVisual from "@/components/seo/SeoVisual";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";
import { buildBreadcrumbStructuredData, buildItemListStructuredData } from "@/lib/structured-data";

export const metadata: Metadata = createSeoMetadata({
  title: "Compare Repository Analysis and Security Workflows",
  description:
    "Compare RepoMind workflows for repository analysis, AI code review, and security scanning across context depth and actionability.",
  canonical: "/compare",
  ogImage: buildOgImageUrl("marketing", { variant: "compare" }),
  ogTitle: "Compare RepoMind Workflows and Alternatives",
  ogDescription: "See how context-aware analysis differs from snippet-first and rule-only workflows.",
});

const comparisonPages = [
  {
    title: "Static Analysis vs RepoMind",
    href: "/static-analysis-vs-repomind",
    summary: "Compare rule-based static analysis and context-aware repository workflows.",
  },
  {
    title: "RepoMind vs SonarQube",
    href: "/repomind-vs-sonarqube",
    summary: "Understand where SonarQube and RepoMind can complement each other.",
  },
  {
    title: "RepoMind vs Snyk",
    href: "/repomind-vs-snyk",
    summary: "Compare security context, triage quality, and actionability.",
  },
];

const breadcrumbSchema = buildBreadcrumbStructuredData([
  { name: "Home", path: "/" },
  { name: "Compare", path: "/compare" },
]);

const itemListSchema = buildItemListStructuredData({
  name: "RepoMind Comparison Guides",
  items: comparisonPages.map((item) => ({ name: item.title, path: item.href })),
});

export default function ComparePage() {
  return (
    <main className="min-h-screen bg-black text-white px-6 py-20">
      <JsonLdScript data={breadcrumbSchema} />
      <JsonLdScript data={itemListSchema} />

      <div className="mx-auto max-w-5xl">
        <nav aria-label="Breadcrumb" className="mb-8 text-sm text-zinc-400 flex items-center gap-2">
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
          <span>/</span>
          <span className="text-zinc-200">Compare</span>
        </nav>

        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-5">Compare Context-Aware Workflows</h1>
        <p className="text-zinc-300 text-lg leading-relaxed max-w-3xl mb-8">
          Use this hub to compare repository analysis approaches across context depth, security signal quality, and engineering actionability.
        </p>

        <section className="mb-10">
          <SeoVisual
            variant="comparison-grid"
            ariaLabel="Comparison matrix for repository analysis workflows"
            sizeMode="wide"
            animate
            priority="high"
          />
        </section>

        <div className="space-y-4 mb-10">
          {comparisonPages.map((track) => (
            <Link key={track.title} href={track.href} className="block rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 hover:bg-zinc-900/60 transition-colors">
              <h2 className="text-xl font-semibold mb-2">{track.title}</h2>
              <p className="text-zinc-400">{track.summary}</p>
            </Link>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          <Link href="/solutions" className="px-5 py-3 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors">
            Explore Solutions
          </Link>
          <Link href="/blog" className="px-5 py-3 rounded-lg bg-white text-black font-medium hover:bg-zinc-200 transition-colors">
            Read Comparison Guides
          </Link>
        </div>
      </div>
    </main>
  );
}
