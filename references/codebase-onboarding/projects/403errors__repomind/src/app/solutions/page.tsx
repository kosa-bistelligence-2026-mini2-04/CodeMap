import type { Metadata } from "next";
import Link from "next/link";
import JsonLdScript from "@/components/JsonLdScript";
import SeoVisual from "@/components/seo/SeoVisual";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";
import {
  buildBreadcrumbStructuredData,
  buildFaqStructuredData,
  buildItemListStructuredData,
  buildSoftwareApplicationStructuredData,
} from "@/lib/structured-data";

export const metadata: Metadata = createSeoMetadata({
  title: "Repository Analysis, AI Code Review, and Security Scanning Solutions",
  description:
    "Explore RepoMind solutions for GitHub repository analysis, AI code review, and security scanning with context-aware workflows and action-ready outputs.",
  canonical: "/solutions",
  keywords: [
    "repository analysis solutions",
    "ai code review solution",
    "repository security scanner",
    "github code analyzer tools",
    "developer security workflow",
    "repomind solutions",
  ],
  ogImage: buildOgImageUrl("marketing", { variant: "solutions" }),
  ogTitle: "RepoMind Solutions for Repository Analysis and Security",
  ogDescription:
    "Choose the right workflow for architecture understanding, review quality, and context-aware security prioritization.",
});

const solutionCards = [
  {
    title: "GitHub Repository Analysis",
    description:
      "Understand architecture, module boundaries, and operational risk before adoption or migration.",
    href: "/github-repository-analysis",
  },
  {
    title: "AI Code Review Tool",
    description:
      "Improve review quality with repository-level context and practical follow-up recommendations.",
    href: "/ai-code-review-tool",
  },
  {
    title: "Security Scanner",
    description:
      "Prioritize high-impact findings with architecture-aware triage and remediation guidance.",
    href: "/security-scanner",
  },
];

const compareLinks = [
  { name: "Static Analysis vs RepoMind", href: "/static-analysis-vs-repomind" },
  { name: "RepoMind vs SonarQube", href: "/repomind-vs-sonarqube" },
  { name: "RepoMind vs Snyk", href: "/repomind-vs-snyk" },
];

const faqItems = [
  {
    question: "What is the best RepoMind solution to start with?",
    answer:
      "Most teams start with GitHub Repository Analysis to build architectural context, then branch into AI Code Review or Security Scanner depending on immediate priorities.",
  },
  {
    question: "Can these workflows be used together in one process?",
    answer:
      "Yes. Teams often analyze architecture first, review implementation quality second, and finish with security triage for release readiness.",
  },
  {
    question: "Which solution is best for onboarding new engineers?",
    answer:
      "GitHub Repository Analysis is usually the fastest path for onboarding because it shortens time-to-understanding on unfamiliar codebases.",
  },
  {
    question: "Does the Security Scanner replace existing AppSec tools?",
    answer:
      "No. It complements existing AppSec tooling by improving prioritization and remediation planning with repository context.",
  },
  {
    question: "How does AI Code Review improve pull request outcomes?",
    answer:
      "It provides context-aware review signals that help teams focus on high-impact logic and dependency risks beyond the diff itself.",
  },
  {
    question: "How should teams measure success after adoption?",
    answer:
      "Common metrics include reduced onboarding time, faster review cycles, and shorter time-to-remediation for high-priority findings.",
  },
];

const breadcrumbSchema = buildBreadcrumbStructuredData([
  { name: "Home", path: "/" },
  { name: "Solutions", path: "/solutions" },
]);

const itemListSchema = buildItemListStructuredData({
  name: "RepoMind Solution Workflows",
  items: solutionCards.map((card) => ({ name: card.title, path: card.href })),
});

const faqSchema = buildFaqStructuredData(faqItems);
const softwareSchema = buildSoftwareApplicationStructuredData({
  name: "RepoMind Solutions",
  description:
    "Integrated workflows for repository analysis, AI code review, and security scanning with context-aware prioritization.",
  path: "/solutions",
  featureList: [
    "GitHub repository analysis",
    "AI code review with repository context",
    "Security triage and remediation prioritization",
    "Workflow-specific comparison guides",
  ],
});

export default function SolutionsPage() {
  return (
    <main className="min-h-screen bg-black text-white px-6 py-20">
      <JsonLdScript data={breadcrumbSchema} />
      <JsonLdScript data={itemListSchema} />
      <JsonLdScript data={faqSchema} />
      <JsonLdScript data={softwareSchema} />

      <div className="mx-auto max-w-6xl">
        <nav aria-label="Breadcrumb" className="mb-8 text-sm text-zinc-400 flex items-center gap-2">
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
          <span>/</span>
          <span className="text-zinc-200">Solutions</span>
        </nav>

        <header className="mb-12">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-5">
            Solutions for Repository Analysis, AI Code Review, and Security Scanning
          </h1>
          <p className="text-zinc-300 text-lg leading-relaxed max-w-4xl mb-5">
            RepoMind gives engineering teams a practical way to move from repository uncertainty to
            informed execution. Instead of switching between disconnected tools, teams can use one
            context-aware workflow family to understand architecture, review implementation, and
            prioritize security remediation.
          </p>
          <p className="text-zinc-400 leading-relaxed max-w-4xl">
            Choose a starting point based on your immediate goal, then connect workflows to build a
            repeatable operating model for onboarding, release readiness, and technical risk reduction.
          </p>
        </header>

        <section className="mb-12">
          <SeoVisual
            variant="hero-flow"
            ariaLabel="RepoMind solutions workflow from repository input to analysis and action"
            sizeMode="wide"
            animate
            priority="high"
          />
        </section>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-12">
          {solutionCards.map((card) => (
            <Link
              key={card.href}
              href={card.href}
              className="block rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 hover:bg-zinc-900/70 hover:border-zinc-700 transition-colors"
            >
              <h2 className="text-xl font-semibold mb-2">{card.title}</h2>
              <p className="text-zinc-400 mb-4 leading-relaxed">{card.description}</p>
              <span className="text-sm text-cyan-300">Open workflow</span>
            </Link>
          ))}
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-12">
          <h2 className="text-2xl font-semibold mb-4">How to choose the right workflow</h2>
          <p className="text-zinc-300 leading-relaxed mb-4">
            Start with <strong>GitHub Repository Analysis</strong> when the primary challenge is understanding
            architecture and module relationships. This is the best first move for onboarding, due diligence,
            or migration planning.
          </p>
          <h3 className="text-xl font-medium mb-2">Use AI Code Review Tool when review quality is the bottleneck</h3>
          <p className="text-zinc-300 leading-relaxed mb-4">
            If pull requests are slow or recurring issues slip through, move into the AI Code Review workflow
            to prioritize high-impact review topics with richer repository context.
          </p>
          <h3 className="text-xl font-medium mb-2">Use Security Scanner when triage speed matters most</h3>
          <p className="text-zinc-300 leading-relaxed">
            When security findings outpace remediation capacity, Security Scanner helps teams focus on likely
            high-impact risks and convert findings into sprint-ready engineering actions.
          </p>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-12">
          <h2 className="text-2xl font-semibold mb-5">Comparison guides for tool selection</h2>
          <p className="text-zinc-400 mb-5 leading-relaxed">
            Use these comparison pages to evaluate workflow fit by context depth, triage quality, and remediation clarity.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {compareLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-xl border border-zinc-700 px-4 py-3 text-zinc-200 hover:bg-zinc-900 transition-colors"
              >
                {item.name}
              </Link>
            ))}
          </div>
        </section>

        <section className="mb-12 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8">
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

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8">
          <h2 className="text-2xl font-semibold mb-3">Take the next step</h2>
          <p className="text-zinc-400 mb-6">
            Start with one repository, then scale the workflow that delivers the fastest measurable impact for your team.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/chat" className="px-5 py-3 rounded-lg bg-white text-black font-medium hover:bg-zinc-200 transition-colors">
              Start Analysis
            </Link>
            <Link href="/explore" className="px-5 py-3 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors">
              Explore SEO Pages
            </Link>
            <Link href="/compare" className="px-5 py-3 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors">
              Compare Workflows
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
