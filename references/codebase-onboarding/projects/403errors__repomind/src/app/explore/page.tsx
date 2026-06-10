import type { Metadata } from "next";
import Link from "next/link";
import JsonLdScript from "@/components/JsonLdScript";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";
import {
  buildBreadcrumbStructuredData,
  buildFaqStructuredData,
  buildItemListStructuredData,
} from "@/lib/structured-data";

export const metadata: Metadata = createSeoMetadata({
  title: "Explore GitHub Analysis and Security Workflows",
  description:
    "Explore live RepoMind pages for GitHub code analysis, AI code review, repository risk analysis, and security workflow comparisons.",
  canonical: "/explore",
  keywords: [
    "explore repository analysis workflows",
    "github analysis pages",
    "security scanner guides",
    "code review workflow hub",
    "repomind comparison pages",
    "software architecture analysis guides",
  ],
  ogImage: buildOgImageUrl("marketing", { variant: "explore" }),
  ogTitle: "Explore RepoMind Workflow Pages",
  ogDescription:
    "Browse live, indexable pages for repository analysis, code review, and security-first engineering decisions.",
});

type TopicEntry = {
  title: string;
  slug: string;
  summary: string;
  category: "Analysis" | "Security" | "Comparison";
};

export const livePages: TopicEntry[] = [
  {
    title: "GitHub Repository Analysis",
    slug: "/github-repository-analysis",
    summary: "Understand architecture, implementation boundaries, and risk hotspots in unfamiliar repositories.",
    category: "Analysis",
  },
  {
    title: "GitHub Code Analyzer",
    slug: "/github-code-analyzer",
    summary: "Analyze repository structure and code behavior with full-file context.",
    category: "Analysis",
  },
  {
    title: "TypeScript Code Analyzer",
    slug: "/typescript-code-analyzer",
    summary: "Navigate large TypeScript repositories with context-aware architecture understanding.",
    category: "Analysis",
  },
  {
    title: "AI Code Review Tool",
    slug: "/ai-code-review-tool",
    summary: "Improve review quality and speed with repository-level context.",
    category: "Analysis",
  },
  {
    title: "Security Scanner",
    slug: "/security-scanner",
    summary: "Prioritize security findings with implementation and architecture context.",
    category: "Security",
  },
  {
    title: "Node.js Security Scanner",
    slug: "/nodejs-security-scanner",
    summary: "Evaluate Node.js repository risk with actionable triage paths.",
    category: "Security",
  },
  {
    title: "Open Source Security Scanner",
    slug: "/open-source-security-scanner",
    summary: "Assess open-source repository security posture before adoption.",
    category: "Security",
  },
  {
    title: "Repository Risk Analysis",
    slug: "/repository-risk-analysis",
    summary: "Evaluate complexity and security exposure for faster engineering decisions.",
    category: "Security",
  },
  {
    title: "Static Analysis vs RepoMind",
    slug: "/static-analysis-vs-repomind",
    summary: "Compare rule-based static analysis and context-aware repository workflows.",
    category: "Comparison",
  },
  {
    title: "RepoMind vs SonarQube",
    slug: "/repomind-vs-sonarqube",
    summary: "Understand where SonarQube and RepoMind are complementary.",
    category: "Comparison",
  },
  {
    title: "RepoMind vs Snyk",
    slug: "/repomind-vs-snyk",
    summary: "Compare security context, triage speed, and workflow fit.",
    category: "Comparison",
  },
];

const grouped = {
  Analysis: livePages.filter((page) => page.category === "Analysis"),
  Security: livePages.filter((page) => page.category === "Security"),
  Comparison: livePages.filter((page) => page.category === "Comparison"),
};

const faqItems = [
  {
    question: "What is the purpose of the Explore page?",
    answer:
      "Explore is the navigation hub for RepoMind analysis, security, and comparison guides so teams can find the right workflow quickly.",
  },
  {
    question: "Are all listed pages indexable and live?",
    answer:
      "Yes. The pages listed in this hub are designed as live, indexable resources for repository analysis and security decision support.",
  },
  {
    question: "Where should I start if I am new to RepoMind?",
    answer:
      "Start with GitHub Repository Analysis for architecture understanding, then move to AI Code Review or Security Scanner based on your immediate goal.",
  },
  {
    question: "How should I use comparison pages?",
    answer:
      "Use comparison pages when selecting tooling strategy, especially when balancing baseline coverage with context-aware triage and remediation planning.",
  },
  {
    question: "Can this help with open-source due diligence?",
    answer:
      "Yes. Use Open Source Security Scanner and Repository Risk Analysis pages to evaluate adoption risk more systematically.",
  },
  {
    question: "Does this page include direct paths to execution?",
    answer:
      "Yes. Each section includes direct links to workflows and the main analysis entry point at /chat.",
  },
];

const breadcrumbSchema = buildBreadcrumbStructuredData([
  { name: "Home", path: "/" },
  { name: "Explore", path: "/explore" },
]);

const itemListSchema = buildItemListStructuredData({
  name: "RepoMind Live Workflow Pages",
  items: livePages.map((entry) => ({ name: entry.title, path: entry.slug })),
});

const faqSchema = buildFaqStructuredData(faqItems);

function ExploreSignalGraphic() {
  return (
    <svg
      role="img"
      aria-label="Explore workflow map for repository analysis and security topics"
      viewBox="0 0 980 300"
      className="w-full h-auto"
    >
      <title>Explore workflow map</title>
      <desc>Interactive map showing analysis, security, and comparison tracks that connect into execution.</desc>
      <rect x="18" y="18" width="944" height="264" rx="18" fill="#09090b" stroke="#27272a" />
      <rect x="60" y="56" width="260" height="68" rx="12" fill="#111827" stroke="#3b82f6" />
      <rect x="360" y="56" width="260" height="68" rx="12" fill="#111827" stroke="#22d3ee" />
      <rect x="660" y="56" width="260" height="68" rx="12" fill="#111827" stroke="#34d399" />
      <text x="190" y="96" textAnchor="middle" fill="#dbeafe" fontSize="18">Analysis Pages</text>
      <text x="490" y="96" textAnchor="middle" fill="#cffafe" fontSize="18">Security Pages</text>
      <text x="790" y="96" textAnchor="middle" fill="#dcfce7" fontSize="18">Comparison Pages</text>

      <line x1="320" y1="90" x2="360" y2="90" stroke="#60a5fa" strokeWidth="3" />
      <line x1="620" y1="90" x2="660" y2="90" stroke="#34d399" strokeWidth="3" />

      <rect x="180" y="176" width="620" height="74" rx="14" fill="#0b1321" stroke="#155e75" />
      <text x="490" y="210" textAnchor="middle" fill="#e0f2fe" fontSize="20">Execution: Analyze, Review, Remediate</text>
      <text x="490" y="234" textAnchor="middle" fill="#94a3b8" fontSize="14">Follow any track to /chat with stronger context and clearer next actions.</text>
    </svg>
  );
}

function TopicSection({
  title,
  items,
}: {
  title: string;
  items: TopicEntry[];
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-zinc-900/40 p-6">
      <h2 className="text-2xl font-semibold mb-5">{title}</h2>
      <ul className="space-y-4">
        {items.map((item) => (
          <li key={item.slug} className="rounded-xl border border-zinc-800 bg-black/20 p-4">
            <Link
              href={item.slug}
              className="text-zinc-100 hover:text-cyan-300 transition-colors font-semibold block mb-1"
            >
              {item.title}
            </Link>
            <p className="text-sm text-zinc-400">{item.summary}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function ExplorePage() {
  return (
    <main className="min-h-screen bg-[#09090b] text-white px-6 py-16">
      <JsonLdScript data={breadcrumbSchema} />
      <JsonLdScript data={itemListSchema} />
      <JsonLdScript data={faqSchema} />

      <div className="mx-auto max-w-6xl">
        <nav aria-label="Breadcrumb" className="mb-8 text-sm text-zinc-400 flex items-center gap-2">
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
          <span>/</span>
          <span className="text-zinc-200">Explore</span>
        </nav>

        <header className="mb-10">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">Explore Live SEO Workflows</h1>
          <p className="text-zinc-300 text-lg mb-4 max-w-5xl leading-relaxed">
            Explore is your fastest route to the full RepoMind content hub for repository analysis,
            AI code review, security scanning, and decision-focused workflow comparisons.
          </p>
          <p className="text-zinc-400 max-w-5xl leading-relaxed">
            Each page in this hub is built for organic discovery and practical execution, with direct
            pathways to deeper analysis and actionable next steps.
          </p>
        </header>

        <section className="mb-10 rounded-2xl border border-white/10 bg-zinc-900/40 p-4">
          <ExploreSignalGraphic />
        </section>

        <section className="rounded-2xl border border-white/10 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-4">How to navigate this hub efficiently</h2>
          <h3 className="text-xl font-medium mb-2">Start with your immediate goal</h3>
          <p className="text-zinc-300 leading-relaxed mb-4">
            Choose Analysis pages when architecture clarity is the priority, Security pages when
            remediation planning is urgent, and Comparison pages when tool strategy decisions are active.
          </p>
          <h3 className="text-xl font-medium mb-2">Connect discovery to execution</h3>
          <p className="text-zinc-300 leading-relaxed">
            Every section links directly to workflow pages and conversion paths so teams can move from
            content discovery to action without losing context.
          </p>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
          <TopicSection title="Code Analysis Pages" items={grouped.Analysis} />
          <TopicSection title="Security Pages" items={grouped.Security} />
          <TopicSection title="Comparison Pages" items={grouped.Comparison} />
          <section className="rounded-2xl border border-white/10 bg-zinc-900/40 p-6">
            <h2 className="text-2xl font-semibold mb-4">Related hubs and actions</h2>
            <p className="text-zinc-400 mb-5">
              Continue through solutions, comparisons, and live analysis workflows.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/solutions" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
                Solutions Hub
              </Link>
              <Link href="/compare" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
                Compare Workflows
              </Link>
              <Link href="/chat" className="px-4 py-2 rounded-lg bg-white text-black font-medium hover:bg-zinc-200 transition-colors">
                Start Analysis
              </Link>
            </div>
          </section>
        </div>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8">
          <h2 className="text-2xl font-semibold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-5">
            {faqItems.map((item) => (
              <article key={item.question} className="border-b border-white/10 pb-4 last:border-0">
                <h3 className="text-lg font-medium mb-2">{item.question}</h3>
                <p className="text-zinc-300 leading-relaxed">{item.answer}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
