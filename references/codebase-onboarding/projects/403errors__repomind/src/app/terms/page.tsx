import type { Metadata } from "next";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";

export const metadata: Metadata = createSeoMetadata({
  title: "Terms of Service",
  description: "Terms of service for using RepoMind responsibly and in compliance with applicable laws and platform policies.",
  canonical: "/terms",
  ogImage: buildOgImageUrl("marketing", { variant: "terms" }),
  ogTitle: "Terms of Service",
  ogDescription: "Terms of service for using RepoMind responsibly and in compliance with applicable laws and platform policies.",
});

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-black text-white px-6 py-20">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">Terms of Service</h1>
        <p className="text-zinc-300 leading-relaxed mb-4">
          By using RepoMind, you agree to use the service responsibly and in compliance with applicable laws and platform policies.
        </p>
        <p className="text-zinc-400 leading-relaxed mb-4">
          We may update features, limits, and policies over time to improve quality and security.
        </p>
        <p className="text-zinc-400 leading-relaxed">
          If you have questions regarding these terms, contact <a href="mailto:pieisnot22by7@gmail.com" className="text-blue-300 hover:text-blue-200">pieisnot22by7@gmail.com</a>.
        </p>
      </div>
    </main>
  );
}
