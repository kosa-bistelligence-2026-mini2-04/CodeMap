import Link from "next/link";
import Image from "next/image";
import { getPublishedPosts } from "@/lib/services/blog-service";
import { ArrowRight, Calendar } from "lucide-react";
import Footer from "@/components/Footer";
import { BlogPost } from "@prisma/client";
import JsonLdScript from "@/components/JsonLdScript";
import { buildOgImageUrl, createSeoMetadata } from "@/lib/seo";
import { buildBreadcrumbStructuredData, buildItemListStructuredData } from "@/lib/structured-data";

export const dynamic = "force-dynamic";

export const metadata = createSeoMetadata({
  title: "Engineering Insights for Repository Analysis and Security",
  description: "Read practical guides on GitHub repository analysis, AI code review, and repository security scanning workflows.",
  canonical: "/blog",
  ogImage: buildOgImageUrl("marketing", { variant: "blog" }),
  ogTitle: "RepoMind Engineering Insights",
  ogDescription: "Practical guides for repository analysis, context-aware review, and security-first engineering.",
});

export default async function BlogIndex() {
  const posts: BlogPost[] = await getPublishedPosts();
  const featuredPost = posts[0];
  const regularPosts = posts.slice(1);
  const breadcrumbSchema = buildBreadcrumbStructuredData([
    { name: "Home", path: "/" },
    { name: "Insights", path: "/blog" },
  ]);
  const itemListSchema = buildItemListStructuredData({
    name: "RepoMind Insights",
    items: posts.map((post) => ({ name: post.title, path: `/blog/${post.slug}` })),
  });

  return (
    <div className="min-h-screen bg-[#09090b] text-white selection:bg-purple-500/30">
      <JsonLdScript data={breadcrumbSchema} />
      <JsonLdScript data={itemListSchema} />

      {/* Header / Nav Placeholder */}
      <div className="border-b border-white/5 bg-[#09090b]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <Link href="/" className="text-xl font-bold bg-gradient-to-r from-purple-400 to-blue-500 bg-clip-text text-transparent">
            RepoMind
          </Link>
          <div className="flex gap-6 items-center">
            <Link href="/" className="text-sm text-zinc-400 hover:text-white transition-colors">Analyzer</Link>
            <Link href="/blog" className="text-sm text-white font-medium">Insights</Link>
            <Link href="https://github.com/403errors/repomind" target="_blank" className="text-sm text-zinc-400 hover:text-white transition-colors">GitHub</Link>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-16">
        <nav aria-label="Breadcrumb" className="mb-8 text-sm text-zinc-400 flex items-center gap-2">
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
          <span>/</span>
          <span className="text-zinc-200">Insights</span>
        </nav>

        {/* Header Section */}
        <div className="mb-16">
          <h1 className="text-5xl font-extrabold mb-4 tracking-tight">
            Engineering <span className="bg-gradient-to-r from-purple-400 to-blue-500 bg-clip-text text-transparent">Insights</span>
          </h1>
          <p className="text-zinc-400 text-lg max-w-2xl">
            Deep dives into GitHub repository analysis, AI code review strategy, and security-first engineering workflows.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/github-repository-analysis" className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors text-sm">
              Repository Analysis
            </Link>
            <Link href="/ai-code-review-tool" className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors text-sm">
              AI Code Review
            </Link>
            <Link href="/security-scanner" className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors text-sm">
              Security Scanner
            </Link>
            <Link href="/explore" className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors text-sm">
              Explore Live Pages
            </Link>
          </div>
        </div>

        {posts.length === 0 ? (
          <div className="py-24 text-center border border-white/5 rounded-3xl bg-zinc-900/20 backdrop-blur-sm">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-purple-500/10 mb-6 border border-purple-500/20">
              <Calendar className="text-purple-400" size={32} />
            </div>
            <h2 className="text-3xl font-bold mb-4">Insights Coming Soon</h2>
            <p className="text-zinc-400 max-w-md mx-auto italic">
              We&apos;re currently deep in the lab building the future of code intelligence. Check back soon for our first deep dives and engineering updates.
            </p>
          </div>
        ) : (
          <>
            {/* Featured Post */}
            {featuredPost && (
              <div className="mb-16">
                <Link href={`/blog/${featuredPost.slug}`}>
                  <div className="conic-border-container rounded-3xl overflow-hidden group">
                    <div className="bg-zinc-900/40 backdrop-blur-xl p-1 md:p-2">
                      <div className="grid md:grid-cols-2 gap-8 items-center p-6 md:p-8">
                        <div className="relative aspect-video rounded-2xl overflow-hidden border border-white/5">
                          <Image 
                            src={featuredPost.image} 
                            alt={featuredPost.title}
                            fill
                            className="object-cover group-hover:scale-105 transition-transform duration-500"
                          />
                        </div>
                        <div>
                          <div className="flex items-center gap-3 mb-4">
                            <span className="px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 text-xs font-bold border border-purple-500/20">
                              {featuredPost.category}
                            </span>
                            <span className="text-zinc-500 text-xs flex items-center gap-1">
                              <Calendar size={12} /> {featuredPost.date}
                            </span>
                          </div>
                          <h2 className="text-3xl font-bold mb-4 group-hover:text-purple-400 transition-colors">
                            {featuredPost.title}
                          </h2>
                          <p className="text-zinc-400 mb-6 line-clamp-3 italic">
                            &ldquo;{featuredPost.excerpt}&rdquo;
                          </p>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-[10px] font-bold">
                                RM
                              </div>
                              <span className="text-sm text-zinc-300 font-medium">{featuredPost.author}</span>
                            </div>
                            <span className="flex items-center gap-1 text-purple-400 text-sm font-bold group-hover:gap-2 transition-all">
                              Read Full Insight <ArrowRight size={16} />
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              </div>
            )}

            {/* Grid Section */}
            <div className="grid md:grid-cols-2 gap-8">
              {regularPosts.map((post) => (
                <Link key={post.slug} href={`/blog/${post.slug}`}>
                  <div className="bg-zinc-900/40 border border-white/5 rounded-3xl p-6 hover:bg-zinc-900/60 hover:border-white/10 transition-all group h-full flex flex-col">
                    <div className="relative aspect-video rounded-xl overflow-hidden mb-6 border border-white/5">
                      <Image 
                        src={post.image} 
                        alt={post.title}
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                      <div className="absolute top-3 left-3">
                        <span className="px-3 py-1 rounded-full bg-black/60 backdrop-blur-md text-white text-[10px] font-bold border border-white/10 uppercase tracking-widest">
                          {post.category}
                        </span>
                      </div>
                    </div>
                    <h3 className="text-xl font-bold mb-3 group-hover:text-purple-400 transition-colors line-clamp-2">
                      {post.title}
                    </h3>
                    <p className="text-zinc-400 text-sm mb-6 line-clamp-2 italic opacity-80">
                      {post.excerpt}
                    </p>
                    <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between">
                      <span className="text-zinc-500 text-[10px] font-bold uppercase tracking-tighter">
                        {post.date}
                      </span>
                      <span className="flex items-center gap-1 text-zinc-300 text-xs font-bold">
                        View <ArrowRight size={14} />
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}
