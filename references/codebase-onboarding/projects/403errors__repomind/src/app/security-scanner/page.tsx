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
  title: "Repository Security Scanner",
  description:
    "Scan GitHub repositories for actionable security risks with RepoMind and prioritize remediation using architecture-aware context.",
  canonical: "/security-scanner",
  keywords: [
    "repository security scanner",
    "github security scanner",
    "ai vulnerability triage",
    "security remediation prioritization",
    "code security analysis tool",
    "developer security workflow",
  ],
  ogImage: buildOgImageUrl("marketing", { variant: "security-scanner" }),
  ogTitle: "Repository Security Scanner with Context-Aware Triage",
  ogDescription:
    "Prioritize findings faster with architecture and implementation context.",
});

const faqItems = [
  {
    question: "What does RepoMind security scanning focus on?",
    answer:
      "RepoMind focuses on practical risk prioritization by pairing findings with architecture and implementation context.",
  },
  {
    question: "Can this support open-source due diligence?",
    answer:
      "Yes. Teams use it during open-source evaluation to understand likely risk impact before adoption.",
  },
  {
    question: "Does this replace all AppSec tooling?",
    answer:
      "No. It complements existing AppSec tools by improving triage quality and remediation clarity inside repositories.",
  },
  {
    question: "Who should use this workflow first?",
    answer:
      "Product security, platform teams, and engineering leads who need faster prioritization in high-change repositories.",
  },
  {
    question: "Can it improve remediation velocity?",
    answer:
      "Yes. Context-aware findings help teams convert alerts into clearer, owner-ready engineering tasks.",
  },
  {
    question: "How should success be measured?",
    answer:
      "Track time-to-triage, time-to-fix for high-severity findings, and recurrence rates in critical services.",
  },
];

const breadcrumbSchema = buildBreadcrumbStructuredData([
  { name: "Home", path: "/" },
  { name: "Solutions", path: "/solutions" },
  { name: "Security Scanner", path: "/security-scanner" },
]);

const faqSchema = buildFaqStructuredData(faqItems);
const softwareSchema = buildSoftwareApplicationStructuredData({
  name: "RepoMind Security Scanner",
  description:
    "Context-aware repository security scanner for actionable risk triage and remediation planning.",
  path: "/security-scanner",
  featureList: [
    "Repository security risk detection",
    "Architecture-aware triage",
    "Prioritized remediation guidance",
    "Cross-team security handoff support",
  ],
});

export default function SecurityScannerPage() {
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
          <span className="text-zinc-200">Security Scanner</span>
        </nav>

        <header className="mb-10">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
            AI Security Scanner for Repositories
          </h1>
          <p className="text-zinc-300 text-lg leading-relaxed mb-4">
            RepoMind helps teams identify and prioritize repository security risks using architecture-aware
            analysis so remediation work starts with the issues most likely to impact real systems.
          </p>
          <p className="text-zinc-400 leading-relaxed">
            Instead of handling alerts in isolation, teams get context-rich guidance that improves triage confidence,
            security-to-engineering handoff, and fix execution speed.
          </p>
        </header>

        <section className="mb-10">
          <SeoVisual
            variant="security-workflow"
            ariaLabel="Repository security workflow from detection to prioritized remediation"
            sizeMode="wide"
            animate
            priority="high"
          />
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-4">Why context-aware security scanning matters</h2>
          <p className="text-zinc-300 leading-relaxed mb-4">
            Security backlogs often grow because findings are difficult to prioritize across busy engineering roadmaps.
            RepoMind improves this by connecting findings to module criticality and implementation behavior.
          </p>
          <h3 className="text-xl font-medium mb-2">Prioritize what can hurt production first</h3>
          <p className="text-zinc-300 leading-relaxed mb-4">
            Teams can focus effort on likely high-impact issues and avoid spending cycles on lower-value noise.
          </p>
          <h3 className="text-xl font-medium mb-2">Improve fix quality and speed</h3>
          <p className="text-zinc-300 leading-relaxed">
            Action-ready remediation guidance helps engineers implement and validate fixes faster with less ambiguity.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2 mb-10">
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Pre-release hardening</h2>
            <p className="text-zinc-400">
              Run a focused scan before release milestones to catch and prioritize high-impact risks.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Open-source package evaluation</h2>
            <p className="text-zinc-400">
              Assess dependency risk posture before introducing new repositories into your stack.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Backlog reduction</h2>
            <p className="text-zinc-400">
              Use context-rich triage to reduce unresolved findings and improve remediation throughput.
            </p>
          </article>
          <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
            <h2 className="text-xl font-semibold mb-2">Cross-team alignment</h2>
            <p className="text-zinc-400">
              Build a shared understanding between AppSec and engineering with clearer prioritization rationale.
            </p>
          </article>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 md:p-8 mb-10">
          <h2 className="text-2xl font-semibold mb-4">Related security workflows</h2>
          <div className="flex flex-wrap gap-3">
            <Link href="/open-source-security-scanner" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Open Source Security Scanner
            </Link>
            <Link href="/nodejs-security-scanner" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Node.js Security Scanner
            </Link>
            <Link href="/repository-risk-analysis" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              Repository Risk Analysis
            </Link>
            <Link href="/repomind-vs-snyk" className="px-4 py-2 rounded-lg border border-zinc-700 hover:bg-zinc-900 transition-colors">
              RepoMind vs Snyk
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
            Run one high-priority security scan and convert findings into a ranked remediation plan this week.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/chat" className="px-5 py-3 rounded-lg bg-white text-black font-medium hover:bg-zinc-200 transition-colors">
              Start Security Scan
            </Link>
            <Link href="/ai-code-review-tool" className="px-5 py-3 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors">
              Continue with AI Code Review
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
