import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, Star, FileCode } from 'lucide-react';
import { getIndexableTopics, getReposForTopic, isIndexableTopic } from '@/lib/repo-catalog';
import { buildOgImageUrl, createSeoMetadata, truncateMetaText } from '@/lib/seo';

interface Props {
    params: Promise<{
        topic: string;
    }>;
}

export const revalidate = 604800;
export const dynamicParams = false;

export async function generateStaticParams() {
    const topics = await getIndexableTopics();
    return topics.map((topic) => ({ topic }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { topic } = await params;
    const topicSlug = decodeURIComponent(topic);
    const displayTopic = topicSlug.replace(/-/g, ' ');
    const capitalizedTopic = displayTopic.charAt(0).toUpperCase() + displayTopic.slice(1);
    const indexable = await isIndexableTopic(topicSlug);
    const repos = await getReposForTopic(topicSlug);
    const topRepo = repos[0];
    const totalStars = repos.reduce((sum, repo) => sum + repo.stars, 0);

    return createSeoMetadata({
        title: `Best Open Source ${capitalizedTopic} Repositories`,
        description: `Discover and analyze the top open-source GitHub repositories for ${displayTopic}. Deep architecture and code analysis powered by RepoMind.`,
        canonical: `/topics/${topic}`,
        ogImage: buildOgImageUrl("topic", {
            topic: displayTopic,
            description: truncateMetaText(`Explore the best open-source projects using ${displayTopic}.`, 170),
            repos: repos.length,
            stars: totalStars,
            topRepo: topRepo ? `${topRepo.owner}/${topRepo.repo}` : undefined,
        }),
        ogTitle: `Top ${capitalizedTopic} repositories`,
        ogDescription: `Explore the best open-source projects using ${displayTopic}.`,
        robots: indexable
            ? { index: true, follow: true }
            : {
                index: false,
                follow: true,
                googleBot: {
                    index: false,
                    follow: true,
                },
            },
    });
}

export default async function TopicPage({ params }: Props) {
    const { topic } = await params;
    const decodedTopic = decodeURIComponent(topic);
    const displayTopic = decodedTopic.replace(/-/g, ' ');

    const repos = await getReposForTopic(decodedTopic);

    if (!repos || repos.length === 0) {
        notFound();
    }

    return (
        <main className="min-h-screen bg-black text-white p-6 md:p-12 overflow-x-hidden relative">
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-10%] right-[-10%] w-[80vw] max-w-[500px] h-[80vw] max-h-[500px] bg-blue-600/10 rounded-full blur-[80px] md:blur-[128px]" />
            </div>

            <div className="max-w-5xl mx-auto relative z-10">
                <Link href="/" className="inline-flex items-center text-zinc-400 hover:text-white mb-8 transition-colors">
                    <ArrowLeft className="w-4 h-4 mr-2" /> back to home
                </Link>

                <header className="mb-16 border-b border-zinc-800 pb-8 text-center md:text-left">
                    <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-4 capitalize">
                        Best Open Source <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">{displayTopic}</span> Libraries
                    </h1>
                    <p className="text-xl text-zinc-300 max-w-3xl">
                        A curated list of the most popular GitHub repositories tagged with <strong>{displayTopic}</strong>.
                        Select any project to visualize its architecture and dive into the codebase using RepoMind&apos;s AI engine.
                    </p>
                </header>

                <div className="grid grid-cols-1 gap-6">
                    {repos.map((repo, index) => (
                        <Link
                            href={`/repo/${repo.owner}/${repo.repo}`}
                            key={`${repo.owner}/${repo.repo}`}
                            className="block w-full bg-zinc-900/50 border border-zinc-800 hover:border-purple-500/50 rounded-xl p-6 transition-all group hover:bg-zinc-900/80"
                        >
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 min-w-0">
                                <div className="min-w-0 flex-1">
                                    <h2 className="text-xl md:text-2xl font-bold mb-2 flex flex-wrap items-center break-all">
                                        <span className="text-zinc-500 mr-3 text-lg shrink-0">#{index + 1}</span>
                                        <span className="text-zinc-300">{repo.owner}/</span>
                                        <span className="text-white group-hover:text-purple-400 transition-colors">{repo.repo}</span>
                                    </h2>
                                    <p className="text-zinc-400 mb-4 line-clamp-2 md:pr-12">{repo.description}</p>

                                    <div className="flex flex-wrap items-center gap-4 text-sm font-medium">
                                        <span className="flex items-center text-yellow-500 bg-yellow-500/10 px-2 py-1 rounded">
                                            <Star className="w-4 h-4 mr-1" />
                                            {repo.stars.toLocaleString()}
                                        </span>
                                        {repo.language && (
                                            <span className="flex items-center text-zinc-300">
                                                <FileCode className="w-4 h-4 mr-1" />
                                                {repo.language}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div className="shrink-0 flex items-center text-purple-400 font-medium">
                                    Explore Repo <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            </div>
        </main>
    );
}
