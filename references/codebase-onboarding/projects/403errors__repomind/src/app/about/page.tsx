import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import {
  BrainCircuit,
  Code2,
  GitBranch,
  ShieldCheck,
  Users,
  Sparkles,
  Compass,
  Globe,
  BookOpen,
  Rocket,
} from "lucide-react";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";
import Footer from "@/components/Footer";
import CAGComparison from "@/components/CAGComparison";
import SecurityBanner from "@/components/SecurityBanner";
import FeaturedIn from "@/components/FeaturedIn";
import JsonLdScript from "@/components/JsonLdScript";
import { FAQ_PAGE_ITEMS } from "@/lib/faq-data";
import { getCanonicalSiteUrl } from "@/lib/site-url";

export const metadata: Metadata = createSeoMetadata({
  title: "About",
  description:
    "RepoMind is an open-source, browser-first platform for GitHub repository and developer profile analysis. Built by Sameer Verma (IIT Madras, @403errors).",
  canonical: "/about",
  ogImage: buildOgImageUrl("marketing", { variant: "about" }),
  ogTitle: "About RepoMind - Built by Sameer Verma",
  ogDescription:
    "Learn how RepoMind delivers full-context repository analysis, AI code review, and security scanning. Built by Sameer Verma (IIT Madras, @403errors).",
  keywords: [
    "RepoMind",
    "About RepoMind",
    "Sameer Verma",
    "IIT Madras",
    "@403errors",
    "Agentic CAG",
    "GitHub repository analysis",
    "AI code review",
    "repository security scanning",
    "open source developer tools",
  ],
});

const audienceCards = [
  {
    title: "Developers evaluating unfamiliar repos",
    description:
      "Understand architecture, dependencies, and behavior without cloning or setting up the project locally.",
    icon: Compass,
  },
  {
    title: "Teams onboarding into large codebases",
    description:
      "Get the mental model fast: entrypoints, modules, and logic paths without hours of manual digging.",
    icon: Users,
  },
  {
    title: "Engineers prioritizing risk and security",
    description:
      "Scan for vulnerabilities and exposure points with full-file context, not isolated snippets.",
    icon: ShieldCheck,
  },
];

const capabilityCards = [
  {
    title: "Full-context repo understanding",
    description:
      "Agentic CAG selects complete, relevant files so the model sees the whole picture instead of fragments.",
    icon: BrainCircuit,
  },
  {
    title: "Architecture + dependency mapping",
    description:
      "Trace entrypoints, flows, and module relationships with visuals that speed up comprehension.",
    icon: GitBranch,
  },
  {
    title: "AI code review with context",
    description:
      "Ask implementation-level questions and get answers grounded in real repository structure.",
    icon: Code2,
  },
  {
    title: "Security & vulnerability scanning",
    description:
      "Surface risk hotspots and security concerns while keeping repository-wide context intact.",
    icon: ShieldCheck,
  },
  {
    title: "Developer profile intelligence",
    description:
      "Analyze GitHub profiles to understand strengths, repositories, and impact quickly.",
    icon: Users,
  },
  {
    title: "Tech stack discovery",
    description:
      "Identify frameworks, dependencies, and versions without manually combing through files.",
    icon: Sparkles,
  },
];

const workflowSteps = [
  {
    title: "Paste a GitHub URL",
    description: "Start from a repository or developer profile, no local setup required.",
  },
  {
    title: "Agentic CAG builds context",
    description: "RepoMind selects full, relevant files to retain true architecture and logic flow.",
  },
  {
    title: "Analyze and visualize",
    description: "Generate architecture maps, review logic, and highlight security risks.",
  },
  {
    title: "Act with confidence",
    description: "Use the output for onboarding, review, due diligence, or security triage.",
  },
];

const galleryItems = [
  {
    title: "Landing & discovery",
    description: "Explore trending repositories and start instantly from a URL.",
    image: "/assets/landing_page.png",
  },
  {
    title: "Repository profile intelligence",
    description: "See core metadata, tech stack, and key findings at a glance.",
    image: "/assets/repo_profile.png",
  },
  {
    title: "Architecture & flow visuals",
    description: "Follow the system path with flowcharts and dependency mapping.",
    image: "/assets/architecture_example.png",
  },
  {
    title: "Security reporting",
    description: "Prioritize vulnerabilities with context-aware findings.",
    image: "/assets/security_report.png",
  },
  {
    title: "Dashboards for ongoing work",
    description: "Track repositories, scans, and progress over time.",
    image: "/assets/dashboard_overview.png",
  },
  {
    title: "Capabilities overview",
    description: "Everything RepoMind can do in one view.",
    image: "/assets/repomind_capabilities.png",
  },
];

const aboutFaqItems = [
  ...FAQ_PAGE_ITEMS.slice(0, 3),
  {
    question: "Who built RepoMind?",
    answer:
      "RepoMind was built by Sameer Verma, an IIT Madras graduate and AI researcher (GitHub @403errors).",
  },
];

export default function AboutPage() {
  const baseUrl = getCanonicalSiteUrl();
  const personSchema = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: "Sameer Verma",
    alumniOf: "IIT Madras",
    description: "AI researcher and creator of RepoMind.",
    sameAs: ["https://github.com/403errors", "https://devsameer.vercel.app"],
    url: `${baseUrl}/about`,
  };
  const aboutSchema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: "About RepoMind",
    url: `${baseUrl}/about`,
    mainEntity: {
      "@type": "SoftwareApplication",
      name: "RepoMind",
      applicationCategory: "DeveloperApplication",
      operatingSystem: "Web",
      url: baseUrl,
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
      },
      creator: {
        "@type": "Person",
        name: "Sameer Verma",
      },
    },
  };

  return (
    <main className="min-h-screen bg-black text-white overflow-x-hidden relative">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[80vw] max-w-[520px] h-[80vw] max-h-[520px] bg-blue-600/30 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[80vw] max-w-[520px] h-[80vw] max-h-[520px] bg-purple-600/30 rounded-full blur-[120px]" />
      </div>

      <section className="relative z-10 px-6 pt-20 pb-16">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-[1.1fr_0.9fr] gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 border border-white/10 rounded-full px-4 py-1 text-xs uppercase tracking-[0.3em] text-zinc-400 mb-6">
              Open Source - Live at repomind.in
            </div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
              About RepoMind
            </h1>
            <p className="text-lg text-zinc-300 leading-relaxed mb-6">
              RepoMind is an open-source, browser-first platform for understanding GitHub repositories and developer profiles through Agentic Context-Augmented Generation (CAG). It lets developers build full mental models without cloning, running, or spelunking through endless files.
            </p>
            <p className="text-zinc-400 leading-relaxed mb-8">
              The mission is simple: stop reading code in fragments and start understanding it end-to-end. RepoMind connects architecture, dependencies, and behavior into answers you can act on quickly.
            </p>
            <p className="text-sm text-zinc-500 mb-8">
              Built by{" "}
              <a
                href="https://devsameer.vercel.app"
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-200 hover:text-white transition-colors"
              >
                Sameer Verma
              </a>{" "}
              (IIT Madras, GitHub @403errors), an AI researcher.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/chat"
                className="px-6 py-3 rounded-xl bg-white text-black font-semibold hover:bg-zinc-200 transition-colors"
              >
                Try RepoMind
              </Link>
              <a
                href="https://github.com/403errors/repomind"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors"
              >
                View on GitHub
              </a>
            </div>
            <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex items-center gap-3 mb-2">
                  <Globe className="w-5 h-5 text-blue-400" />
                  <span className="font-semibold">Browser-first workflow</span>
                </div>
                <p className="text-sm text-zinc-400">
                  Go from URL to understanding without cloning or local setup.
                </p>
              </div>
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex items-center gap-3 mb-2">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                  <span className="font-semibold">Full-file context</span>
                </div>
                <p className="text-sm text-zinc-400">
                  Agentic CAG loads entire, relevant files to preserve logic and architecture.
                </p>
              </div>
            </div>
          </div>

          <div className="relative">
            <div className="absolute -inset-4 bg-gradient-to-b from-blue-500/20 to-purple-500/5 blur-2xl rounded-3xl" />
            <div className="relative rounded-3xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-2xl">
              <div className="relative w-full pt-[56.25%]">
                <iframe
                  src="https://www.youtube.com/embed/3f66xlgpjw0"
                  title="RepoMind demo"
                  className="absolute inset-0 h-full w-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            </div>
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <BrainCircuit className="w-4 h-4 text-cyan-400" />
                  Agentic CAG
                </div>
                <p className="text-xs text-zinc-400 mt-2">
                  Full-context analysis instead of fragmented chunk retrieval.
                </p>
              </div>
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <ShieldCheck className="w-4 h-4 text-green-400" />
                  Security scanning
                </div>
                <p className="text-xs text-zinc-400 mt-2">
                  Context-aware risk discovery built into the workflow.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
              Who RepoMind Is For
            </h2>
            <p className="text-zinc-400 text-lg">
              Built for developers who need fast clarity, not another slow setup cycle.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {audienceCards.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.title}
                  className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6"
                >
                  <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4">
                    <Icon className="w-6 h-6 text-blue-300" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                  <p className="text-zinc-400 text-sm leading-relaxed">{item.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 py-20 bg-zinc-950 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
              What RepoMind Does
            </h2>
            <p className="text-zinc-400 text-lg mb-8">
              From architecture clarity to security insights, RepoMind turns entire repositories into an understandable, actionable narrative.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {capabilityCards.map((item) => {
                const Icon = item.icon;
                return (
                  <div
                    key={item.title}
                    className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <Icon className="w-5 h-5 text-purple-300" />
                      <span className="font-semibold text-sm">{item.title}</span>
                    </div>
                    <p className="text-xs text-zinc-400 leading-relaxed">{item.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">How RepoMind Works</h2>
            <p className="text-zinc-400 text-lg">
              A workflow designed for understanding, not just retrieval.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {workflowSteps.map((step, index) => (
              <div
                key={step.title}
                className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5"
              >
                <div className="text-xs uppercase tracking-[0.3em] text-zinc-500 mb-2">Step {index + 1}</div>
                <h3 className="font-semibold mb-2">{step.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed">{step.description}</p>
              </div>
            ))}
          </div>
          <div className="mt-10 grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-6 items-center">
            <div className="rounded-3xl border border-zinc-800 bg-zinc-900/30 p-4">
              <Image
                src="/assets/architecture_example.png"
                alt="Architecture visualization example"
                width={1000}
                height={720}
                className="w-full h-auto rounded-2xl"
              />
            </div>
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
              <div className="flex items-center gap-3 mb-3">
                <GitBranch className="w-5 h-5 text-cyan-400" />
                <h3 className="text-xl font-semibold">Architecture-first answers</h3>
              </div>
              <p className="text-zinc-400 text-sm leading-relaxed">
                RepoMind connects entrypoints, services, and dependencies so you can reason about behavior end-to-end, not just isolated files.
              </p>
              <div className="mt-4 flex items-center gap-2 text-xs text-zinc-500">
                <Rocket className="w-4 h-4" />
                Designed for onboarding, due diligence, and decision-making.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 py-20 bg-zinc-950 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Product Visuals</h2>
            <p className="text-zinc-400 text-lg">
              Screens and flows from RepoMind in action.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {galleryItems.map((item) => (
              <div
                key={item.title}
                className="rounded-3xl border border-zinc-800 bg-zinc-900/40 p-4"
              >
                <div className="rounded-2xl overflow-hidden border border-zinc-800">
                  <Image
                    src={item.image}
                    alt={item.title}
                    width={960}
                    height={720}
                    className="w-full h-auto"
                  />
                </div>
                <div className="mt-4">
                  <h3 className="text-lg font-semibold mb-1">{item.title}</h3>
                  <p className="text-zinc-400 text-sm">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-[0.9fr_1.1fr] gap-10 items-center">
          <div className="rounded-3xl border border-zinc-800 bg-zinc-900/40 p-4">
            <Image
              src="/assets/cag_vs_rag.gif"
              alt="Agentic CAG vs traditional RAG"
              width={900}
              height={720}
              unoptimized
              className="w-full h-auto rounded-2xl"
            />
          </div>
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-1 border border-blue-500/30 rounded-full text-xs uppercase tracking-[0.3em] text-blue-300 mb-4">
              Why Agentic CAG
            </div>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
              Full Context Beats Fragmented Retrieval
            </h2>
            <p className="text-zinc-400 text-lg mb-6">
              Standard "chat with your code" tools often rely on RAG-style chunking. RepoMind uses Agentic CAG to pull complete, relevant files so the model sees the real architecture and logic flow.
            </p>
            <ul className="space-y-3 text-sm text-zinc-300">
              <li className="flex items-start gap-3">
                <span className="mt-1 w-2 h-2 rounded-full bg-blue-400" />
                Preserves full-file context for reliable reasoning.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 w-2 h-2 rounded-full bg-purple-400" />
                Avoids missing logic hidden behind imports and indirection.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 w-2 h-2 rounded-full bg-cyan-400" />
                Produces architecture-level answers, not just snippet summaries.
              </li>
            </ul>
          </div>
        </div>
      </section>

      <CAGComparison />

      <section className="relative z-10 px-6 py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-4 py-1 border border-white/10 rounded-full text-xs uppercase tracking-[0.3em] text-zinc-500 mb-4">
              Founder Story
            </div>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
              Built by Sameer Verma
            </h2>
            <p className="text-zinc-300 text-lg leading-relaxed mb-4">
              Sameer Verma is an IIT Madras graduate, GitHub <span className="text-white font-semibold">@403errors</span>, and an AI researcher. RepoMind started as a personal project when he needed a faster way to understand GitHub repositories without hitting paywalls or waiting endlessly for fragmented answers.
            </p>
            <p className="text-zinc-400 leading-relaxed mb-6">
              The result is RepoMind (repomind.in): a fully open-source tool that uses Agentic CAG instead of RAG to keep codebase context intact and make repository understanding dramatically faster.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="https://github.com/403errors"
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2 rounded-xl border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors"
              >
                GitHub @403errors
              </a>
              <a
                href="https://devsameer.vercel.app"
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2 rounded-xl border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors"
              >
                devsameer.vercel.app
              </a>
              <Link
                href="/chat"
                className="px-5 py-2 rounded-xl bg-white text-black font-semibold hover:bg-zinc-200 transition-colors"
              >
                Try RepoMind
              </Link>
            </div>
          </div>
          <div className="rounded-3xl border border-zinc-800 bg-zinc-900/40 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Image
                src="/1080x1080.png"
                alt="RepoMind logo"
                width={64}
                height={64}
                className="rounded-2xl"
              />
              <div>
                <div className="text-sm uppercase tracking-[0.3em] text-zinc-500">Open Source</div>
                <div className="text-xl font-semibold">MIT Licensed</div>
              </div>
            </div>
            <div className="space-y-4 text-sm text-zinc-400">
              <p>
                RepoMind is live and free to use for public repository analysis, with fair-use limits on heavy tool calls to keep the platform fast and accessible.
              </p>
              <p>
                Anonymous users can run Lite analysis, while signed-in users unlock higher limits and Thinking mode for deeper context.
              </p>
            </div>
            <div className="mt-6 rounded-2xl border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-500">
              <span className="text-zinc-300 font-semibold">Open source repo:</span> github.com/403errors/repomind
            </div>
          </div>
        </div>
      </section>

      <FeaturedIn />
      <SecurityBanner />

      <section className="relative z-10 px-6 py-20 border-t border-white/5">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">Frequently Asked</h2>
            <p className="text-zinc-400 text-lg">Quick answers from the RepoMind workflow.</p>
          </div>
          <div className="space-y-4">
            {aboutFaqItems.map((item) => (
              <div
                key={item.question}
                className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6"
              >
                <h3 className="text-lg font-semibold mb-2">{item.question}</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">{item.answer}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative z-10 px-6 py-20 bg-zinc-950 border-t border-white/5">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1 border border-white/10 rounded-full text-xs uppercase tracking-[0.3em] text-zinc-500 mb-4">
            Ready to explore
          </div>
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
            Try RepoMind on your next repository
          </h2>
          <p className="text-zinc-400 text-lg mb-8">
            Paste a GitHub URL and get architecture, review, and security insights instantly.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/chat"
              className="px-6 py-3 rounded-xl bg-white text-black font-semibold hover:bg-zinc-200 transition-colors"
            >
              Try RepoMind
            </Link>
            <Link
              href="/github-repository-analysis"
              className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors"
            >
              Explore the Workflow
            </Link>
          </div>
        </div>
      </section>

      <Footer />
      <JsonLdScript data={personSchema} />
      <JsonLdScript data={aboutSchema} />
    </main>
  );
}
