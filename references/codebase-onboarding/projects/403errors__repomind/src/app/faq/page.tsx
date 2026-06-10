import { Metadata } from "next";
import Link from "next/link";
import JsonLdScript from "@/components/JsonLdScript";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";
import { buildBreadcrumbStructuredData, buildFaqStructuredData } from "@/lib/structured-data";
import { FAQ_PAGE_ITEMS } from "@/lib/faq-data";

export const metadata: Metadata = createSeoMetadata({
    title: "FAQ",
    description: "Frequently asked questions about RepoMind's Agentic CAG, GitHub repository analysis, architecture visualization, and security scanning.",
    canonical: "/faq",
    ogImage: buildOgImageUrl("marketing", { variant: "faq" }),
    ogTitle: "RepoMind FAQ",
    ogDescription: "Frequently asked questions about RepoMind's repository analysis and security scanning.",
});

export default function FAQPage() {
    const faqSchema = buildFaqStructuredData(FAQ_PAGE_ITEMS.map((faq) => ({
        question: faq.question,
        answer: faq.answer,
    })));
    const breadcrumbSchema = buildBreadcrumbStructuredData([
        { name: "Home", path: "/" },
        { name: "FAQ", path: "/faq" },
    ]);

    return (
        <main className="min-h-screen max-w-4xl mx-auto py-24 px-6">
            <JsonLdScript data={faqSchema} />
            <JsonLdScript data={breadcrumbSchema} />

            <nav aria-label="Breadcrumb" className="mb-8 text-sm text-zinc-400 flex items-center gap-2">
                <Link href="/" className="hover:text-white transition-colors">Home</Link>
                <span>/</span>
                <span className="text-zinc-200">FAQ</span>
            </nav>
            
            <div className="mb-12">
                <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 text-white">Frequently Asked Questions</h1>
                <p className="text-lg text-zinc-400">Everything you need to know about analyzing, visualizing, and querying GitHub repositories with RepoMind.</p>
            </div>

            <div className="space-y-8">
                {FAQ_PAGE_ITEMS.map((faq, index) => (
                    <div key={index} className="border-b border-white/10 pb-6 last:border-0">
                        <h2 className="text-xl font-semibold mb-3 text-white">{faq.question}</h2>
                        <p className="text-zinc-400 leading-relaxed">{faq.answer}</p>
                    </div>
                ))}
            </div>
            
            <div className="mt-16 text-center">
                <Link href="/" className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-black bg-white hover:bg-zinc-200 transition-colors">
                    Start Analyzing for Free
                </Link>
            </div>
        </main>
    );
}
