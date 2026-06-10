import type { Metadata } from "next";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";

export const metadata: Metadata = createSeoMetadata({
  title: "Privacy Policy",
  description: "How RepoMind handles account data, usage analytics, authentication, and scan-related information.",
  canonical: "/privacy",
  ogImage: buildOgImageUrl("marketing", { variant: "privacy" }),
  ogTitle: "Privacy Policy",
  ogDescription: "How RepoMind handles account data, usage analytics, authentication, and scan-related information.",
});

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-black text-white px-6 py-20">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">Privacy Policy</h1>
        <p className="text-zinc-300 leading-relaxed mb-4">
          RepoMind respects your privacy. We only collect data required to operate the product and improve reliability.
        </p>
        <p className="text-zinc-400 leading-relaxed mb-4">
          Usage analytics, authentication details, and account-related metadata may be processed to provide features and support.
        </p>
        <p className="text-zinc-400 leading-relaxed">
          For data-related requests, contact us at <a href="mailto:pieisnot22by7@gmail.com" className="text-blue-300 hover:text-blue-200">pieisnot22by7@gmail.com</a>.
        </p>
      </div>
    </main>
  );
}
