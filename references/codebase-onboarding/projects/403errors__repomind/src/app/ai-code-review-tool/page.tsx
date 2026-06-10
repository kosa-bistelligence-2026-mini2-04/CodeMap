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
  title: "AI Code Review Tool",
  description:
    "Use RepoMind as an AI code review tool to review implementation quality with full repository context, clearer prioritization, and faster feedback loops.",
  canonical: "/ai-code-review-tool",
  keywords: [
    "ai code review tool",
    "context aware code review",
    "repository code review",
    "code review automation",
    "pull request quality tool",
    "github ai reviewer",
  ],
  ogImage: buildOgImageUrl("marketing", { variant: "ai-code-review-tool" }),
  ogTitle: "AI Code Review with Full Repository Context",
  ogDescription:
    "Reduce review blind spots and speed up feedback loops with context-aware repository analysis.",
});

const faqItems = [
  {
    question: "How is this different from reviewing a pull request diff alone?",
    answer:
      "RepoMind incorporates repository context so review comments account for architecture and dependency impact beyond the immediate diff.",
  },
  {
    question: "Can this reduce review cycle time?",
    answer:
      "Yes. Teams often reduce cycle time by focusing review attention on high-impact logic and integration paths earlier.",
  },
  {
    question: "Does this work for large codebases with shared modules?",
    answer:
      "Yes. Context-aware analysis helps reviewers understand shared module impact and avoid local-only conclusions.",
  },
  {
    question: "Who should use this workflow first?",
    answer:
      "Engineering leads, senior reviewers, and platform teams usually see the fastest value because they review high-impact changes frequently.",
  },
  {
    question: "Can this complement existing CI quality checks?",
    answer:
      "Yes. CI checks enforce baseline quality, while RepoMind strengthens contextual interpretation during review.",
  },
  {
    question: "What is a good success metric after rollout?",
    answer:
      "Track review turnaround time, reopened PR rate, and post-merge defect escape rate for critical repositories.",
  },
];

const breadcrumbSchema = buildBreadcrumbStructuredData([
  { name: "Home", path: "/" },
  { name: "Solutions", path: "/solutions" },
  { name: "AI Code Review Tool", path: "/ai-code-review-tool" },
]);

const faqSchema = buildFaqStructuredData(faqItems);
const softwareSchema = buildSoftwareApplicationStructuredData({
  name: "RepoMind AI Code Review Tool",
  description:
    "Context-aware AI code review workflow for faster, higher-confidence implementation review.",
  path: "/ai-code-review-tool",
  featureList: [
    "Repository-wide review context",
    "Architecture-aware review signals",
    "Dependency impact visibility",
    "Action-oriented review outcomes",
  ],
});

export default function AICodeReviewToolPage() {
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
          <span className="text-zinc-200">AI Code Review Tool</span>
        </nav>

        <header className="mb-10">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
            AI Code Review Tool with Full-File Context
          </h1>
          <p className="text-zinc-300 text-lg leading-relaxed mb-4">
            RepoMind helps engineering teams review code with repository-level context, making it easier
            to catch high-impact issues before merge and reduce slow, repetitive review cycles.
          </p>
          <p className="text-zinc-400 leading-relaxed">
            Instead of local-only diff reading, this workflow highlights architecture side effects,
            dependency impact, and probable risk areas so reviewers can focus on what matters first.
          </p>
        </header>

        <section className="mb-10">
          <SeoVisual
            variant="review-workflow"
            ariaLabel="AI code review workflow from review intent to actionable feedback"
            sizeMode="wide"
            animate
            priority="high"
          />
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-4">How this AI code review workflow works</h2>
          <p className="text-zinc-300 leading-relaxed mb-4">
            RepoMind starts with review intent, then evaluates changes with broader repository context.
            This helps reviewers understand how a modification may affect behavior in adjacent modules and
            where regression risk is most likely.
          </p>
          <h3 className="text-xl font-medium mb-2">Context before comment quality</h3>
          <p className="text-zinc-300 leading-relaxed mb-4">
            Better context improves feedback quality, lowers misprioritized comments, and makes review outcomes easier to action.
          </p>
          <h3 className="text-xl font-medium mb-2">Action-ready outcomes for teams</h3>
          <p className="text-zinc-300 leading-relaxed">
            Teams can move from findings to concrete follow-up tasks with clearer ownership and sequencing.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2 mb-10">
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Review quality</h2>
            <p className="text-zinc-400">
              Catch hidden dependencies and system-level side effects that are easy to miss in diff-only reviews.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Reviewer productivity</h2>
            <p className="text-zinc-400">
              Spend less time rebuilding context and more time validating critical implementation decisions.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Team consistency</h2>
            <p className="text-zinc-400">
              Standardize how high-risk changes are reviewed across teams and repositories.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Release confidence</h2>
            <p className="text-zinc-400">
              Improve confidence before merge by highlighting areas that need deeper validation.
            </p>
          </article>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-4">Related review and analysis paths</h2>
          <div className="flex flex-wrap gap-3">
            <Link href="/github-repository-analysis" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              GitHub Repository Analysis
            </Link>
            <Link href="/static-analysis-vs-repomind" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Static Analysis vs RepoMind
            </Link>
            <Link href="/security-scanner" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Security Scanner
            </Link>
            <Link href="/compare" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Comparison Hub
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
            Run context-aware review on your highest-change repository and improve review outcomes this sprint.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/chat" className="px-5 py-3 rounded-lg bg-white text-black font-medium hover:bg-zinc-200 transition-colors">
              Start AI Code Review
            </Link>
            <Link href="/github-repository-analysis" className="px-5 py-3 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors">
              Analyze Repository Architecture
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
