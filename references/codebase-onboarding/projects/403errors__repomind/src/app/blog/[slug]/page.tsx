import { getPublishedPostBySlug, getPublishedPosts } from "@/lib/services/blog-service";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Clock, Share2 } from "lucide-react";
import Footer from "@/components/Footer";
import { EnhancedMarkdown } from "@/components/EnhancedMarkdown";
import JsonLdScript from "@/components/JsonLdScript";
import { BlogPost } from "@prisma/client";
import { Metadata } from "next";
import { buildOgImageUrl, createSeoMetadata, truncateMetaText } from "@/lib/seo";
import { buildBlogPostingStructuredData, buildBreadcrumbStructuredData } from "@/lib/structured-data";

// Generates static params for all blog posts
export async function generateStaticParams() {
  const posts: BlogPost[] = await getPublishedPosts();
  return posts.map((post) => ({
    slug: post.slug,
  }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPublishedPostBySlug(slug);

  if (!post) {
    return createSeoMetadata({
      title: "Post Not Found",
      description: "This blog post could not be found.",
      canonical: "/blog",
      ogImage: buildOgImageUrl("marketing", { variant: "home" }),
      ogTitle: "Post Not Found",
      ogDescription: "This blog post could not be found.",
      noIndex: true,
    });
  }

  const canonicalPath = `/blog/${post.slug}`;
  const publishedTime = (post.publishedAt ?? post.createdAt).toISOString();

  const description = truncateMetaText(post.excerpt, 180);
  const keywords = typeof post.keywords === "string"
    ? post.keywords
        .split(",")
        .map((keyword) => keyword.trim())
        .filter(Boolean)
    : undefined;

  const metadata = createSeoMetadata({
    title: post.title,
    description,
    keywords,
    canonical: canonicalPath,
    ogImage: buildOgImageUrl("blog", {
      title: post.title,
      description,
      category: post.category,
      image: post.image,
      author: post.author,
    }),
    ogTitle: post.title,
    ogDescription: description,
    ogType: "article",
    twitterImage: post.image,
    twitterTitle: post.title,
    twitterDescription: description,
  });

  metadata.openGraph = {
    ...metadata.openGraph,
    type: "article",
    url: canonicalPath,
    publishedTime,
    modifiedTime: post.updatedAt.toISOString(),
    authors: [post.author],
  };

  return metadata;
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await getPublishedPostBySlug(slug);

  if (!post) {
    notFound();
  }

  const blogPostingSchema = buildBlogPostingStructuredData({
    title: post.title,
    excerpt: post.excerpt,
    image: post.image,
    author: post.author,
    slug: post.slug,
    publishedAtIso: (post.publishedAt || post.createdAt).toISOString(),
    updatedAtIso: post.updatedAt.toISOString(),
  });

  const breadcrumbSchema = buildBreadcrumbStructuredData([
    { name: "Home", path: "/" },
    { name: "Insights", path: "/blog" },
    { name: post.title, path: `/blog/${post.slug}` },
  ]);

  return (
    <div className="min-h-screen bg-[#09090b] text-white">
      <JsonLdScript data={blogPostingSchema} />
      <JsonLdScript data={breadcrumbSchema} />

       {/* Header / Nav */}
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

      <main className="max-w-4xl mx-auto px-6 py-16">
        <nav aria-label="Breadcrumb" className="mb-6 text-sm text-zinc-400 flex items-center gap-2">
          <Link href="/" className="hover:text-white transition-colors">Home</Link>
          <span>/</span>
          <Link href="/blog" className="hover:text-white transition-colors">Insights</Link>
          <span>/</span>
          <span className="text-zinc-200 line-clamp-1">{post.title}</span>
        </nav>

        <Link 
          href="/blog" 
          className="inline-flex items-center gap-2 text-zinc-400 hover:text-white transition-colors mb-12 text-sm font-medium"
        >
          <ArrowLeft size={16} /> Back to Insights
        </Link>

        {/* Post Metadata */}
        <div className="mb-12">
            <div className="flex items-center gap-3 mb-6">
                <span className="px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 text-[10px] font-bold border border-purple-500/20 uppercase tracking-widest">
                    {post.category}
                </span>
                <span className="text-zinc-500 text-xs flex items-center gap-1">
                    <Clock size={12} /> 5 min read
                </span>
            </div>
            <h1 className="text-4xl md:text-6xl font-extrabold mb-8 tracking-tight leading-tight">
                {post.title}
            </h1>
            <div className="flex items-center justify-between py-6 border-y border-white/5">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center font-bold">
                        RM
                    </div>
                    <div>
                        <p className="text-sm font-bold">{post.author}</p>
                        <p className="text-xs text-zinc-500">{post.date}</p>
                    </div>
                </div>
                <div className="flex gap-4">
                    <button className="p-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
                        <Share2 size={18} className="text-zinc-400" />
                    </button>
                </div>
            </div>
        </div>

        {/* Hero Image */}
        <div className="relative rounded-3xl overflow-hidden mb-16 border border-white/5 shadow-2xl bg-zinc-900/50">
            <img 
                src={post.image} 
                alt={post.title}
                className="w-full h-auto block"
            />
        </div>

        {/* Post Content */}
        <div className="prose prose-invert prose-purple max-w-none">
            <p className="text-zinc-300 text-lg not-prose mb-8 leading-relaxed">
              {post.excerpt}
            </p>
            <EnhancedMarkdown content={post.content} />
        </div>

        <section className="mt-14 rounded-2xl border border-white/10 bg-zinc-900/40 p-6">
          <h3 className="text-xl font-semibold mb-4">Related Workflows</h3>
          <div className="flex flex-wrap gap-3">
            <Link href="/github-repository-analysis" className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors text-sm">
              GitHub Repository Analysis
            </Link>
            <Link href="/ai-code-review-tool" className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors text-sm">
              AI Code Review Tool
            </Link>
            <Link href="/security-scanner" className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-200 hover:bg-zinc-900 transition-colors text-sm">
              Security Scanner
            </Link>
          </div>
        </section>

        {/* CTA */}
        <div className="mt-20 pt-12 border-t border-white/5 text-center">
            <h4 className="text-sm font-bold uppercase tracking-[0.2em] text-purple-400 mb-8">Ready to see it in action?</h4>
            <Link 
                href="/" 
                className="inline-block bg-gradient-to-r from-purple-500 to-blue-500 text-white font-bold px-8 py-4 rounded-2xl hover:opacity-90 transition-opacity shadow-lg shadow-purple-500/20"
            >
                Start Analyzing Repos Now
            </Link>
        </div>
      </main>

      <Footer />
    </div>
  );
}
