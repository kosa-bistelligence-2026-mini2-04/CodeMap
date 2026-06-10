import type { Metadata } from "next";
import Link from "next/link";
import JsonLdScript from "@/components/JsonLdScript";
import SeoVisual from "@/components/seo/SeoVisual";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";
import {
  buildBreadcrumbStructuredData,
  buildFaqStructuredData,
  buildSoftwareApplicationStructuredData,
} from "@/lib/structured-data";

export const metadata: Metadata = createSeoMetadata({
  title: "GitHub Repository Analysis",
  description:
    "Run full-context GitHub repository analysis with RepoMind to map architecture, understand implementation behavior, and prioritize repository risk.",
  canonical: "/github-repository-analysis",
  keywords: [
    "github repository analysis",
    "analyze github repo architecture",
    "repository due diligence tool",
    "codebase architecture mapping",
    "repository risk assessment",
    "ai repository analyzer",
  ],
  ogImage: buildOgImageUrl("marketing", { variant: "github-repository-analysis" }),
  ogTitle: "GitHub Repository Analysis for Faster Engineering Decisions",
  ogDescription:
    "Understand unfamiliar repositories faster before integrating, reviewing, or contributing.",
});

const faqItems = [
  {
    question: "What is GitHub repository analysis in RepoMind?",
    answer:
      "It is a workflow that maps architecture, behavior paths, and risk hotspots so teams can make faster technical decisions.",
  },
  {
    question: "When should teams run repository analysis?",
    answer:
      "Run it during onboarding, due diligence, migration planning, security triage preparation, and major release checkpoints.",
  },
  {
    question: "Can this be used for open-source adoption decisions?",
    answer:
      "Yes. Teams use it to evaluate maintainability, architecture complexity, and likely remediation effort before adoption.",
  },
  {
    question: "Who benefits the most from this workflow?",
    answer:
      "Platform teams, senior engineers, technical leads, and security reviewers who need fast context on unfamiliar codebases.",
  },
  {
    question: "Does it replace code review or security scanning?",
    answer:
      "No. It complements both by establishing a shared architecture context before deeper review and security workflows.",
  },
  {
    question: "What should happen after the first analysis run?",
    answer:
      "Use identified hotspots to prioritize review and security actions, then track improvements through recurring analysis checkpoints.",
  },
];

const breadcrumbSchema = buildBreadcrumbStructuredData([
  { name: "Home", path: "/" },
  { name: "Solutions", path: "/solutions" },
  { name: "GitHub Repository Analysis", path: "/github-repository-analysis" },
]);

const faqSchema = buildFaqStructuredData(faqItems);
const softwareSchema = buildSoftwareApplicationStructuredData({
  name: "RepoMind GitHub Repository Analysis",
  description:
    "Repository analysis workflow for architecture understanding, behavior interpretation, and risk prioritization.",
  path: "/github-repository-analysis",
  featureList: [
    "Architecture and dependency mapping",
    "Behavior path interpretation",
    "Risk hotspot identification",
    "Action-oriented analysis outputs",
  ],
});

export default function GitHubRepositoryAnalysisPage() {
  return (
    <main className="min-h-screen bg-black text-white px-6 py-20">
      <JsonLdScript data={breadcrumbSchema} />
      <JsonLdScript data={faqSchema} />
      <JsonLdScript data={softwareSchema} />

      <div className="mx-auto max-w-5xl">
        <nav aria-label="Breadcrumb" className="mb-8 text-sm text-zinc-400 flex items-center gap-2">
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
          <span>/</span>
          <Link href="/solutions" className="hover:text-white transition-colors">Solutions</Link>
          <span>/</span>
          <span className="text-zinc-200">GitHub Repository Analysis</span>
        </nav>

        <header className="mb-10">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
            GitHub Repository Analysis with Full-Context AI
          </h1>
          <p className="text-zinc-300 text-lg leading-relaxed mb-4">
            RepoMind helps teams evaluate unfamiliar repositories by mapping architecture, tracing
            implementation behavior, and surfacing risk hotspots that affect delivery confidence.
          </p>
          <p className="text-zinc-400 leading-relaxed">
            The workflow is designed for practical decisions: whether to adopt a dependency, how to
            onboard quickly, and where to focus review effort when timelines are tight.
          </p>
        </header>

        <section className="mb-10">
          <SeoVisual
            variant="analysis-workflow"
            ariaLabel="GitHub repository analysis workflow from ingest to insights"
            sizeMode="wide"
            animate
            priority="high"
          />
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-4">What this workflow delivers</h2>
          <p className="text-zinc-300 leading-relaxed mb-4">
            RepoMind does more than summarize files. It highlights how modules connect, where critical
            logic resides, and which areas deserve deeper review before engineering investment increases.
          </p>
          <h3 className="text-xl font-medium mb-2">Architecture clarity for faster onboarding</h3>
          <p className="text-zinc-300 leading-relaxed mb-4">
            Teams can understand major boundaries and dependencies early, reducing time spent in manual code discovery.
          </p>
          <h3 className="text-xl font-medium mb-2">Risk visibility before expensive decisions</h3>
          <p className="text-zinc-300 leading-relaxed">
            By revealing high-impact hotspots and fragile paths, teams can prioritize mitigation before they commit to integrations or rewrites.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2 mb-10">
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Due diligence</h2>
            <p className="text-zinc-400">
              Evaluate open-source or third-party repositories for maintainability and risk before integration.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Onboarding</h2>
            <p className="text-zinc-400">
              Help new engineers understand architecture faster and contribute with fewer review cycles.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Migration planning</h2>
            <p className="text-zinc-400">
              Identify critical module dependencies and likely migration friction before planning execution.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Security preparation</h2>
            <p className="text-zinc-400">
              Establish repository context first so security findings can be prioritized with better confidence.
            </p>
          </article>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-4">Related analysis paths</h2>
          <div className="flex flex-wrap gap-3">
            <Link href="/github-code-analyzer" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              GitHub Code Analyzer
            </Link>
            <Link href="/typescript-code-analyzer" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              TypeScript Code Analyzer
            </Link>
            <Link href="/repository-risk-analysis" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Repository Risk Analysis
            </Link>
            <Link href="/security-scanner" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Security Scanner
            </Link>
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-5">
            {faqItems.map((faq) => (
              <article key={faq.question} className="border-b border-white/10 pb-4 last:border-0">
                <h3 className="text-lg font-medium mb-2">{faq.question}</h3>
                <p className="text-zinc-300 leading-relaxed">{faq.answer}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8">
          <h2 className="text-2xl font-semibold mb-2">Take the next step</h2>
          <p className="text-zinc-400 mb-6">
            Analyze one critical repository and convert context into a prioritized review and security plan.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/chat" className="px-5 py-3 rounded-lg bg-white text-black font-medium hover:bg-zinc-200 transition-colors">
              Analyze a GitHub Repository
            </Link>
            <Link href="/ai-code-review-tool" className="px-5 py-3 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors">
              Open AI Code Review Tool
            </Link>
            <Link href="/solutions" className="px-5 py-3 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors">
              Back to Solutions
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
