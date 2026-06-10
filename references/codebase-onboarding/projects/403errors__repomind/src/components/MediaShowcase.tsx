"use client";

import { motion } from "framer-motion";
import { Youtube, BookOpen, ArrowRight } from "lucide-react";
import Image from "next/image";

const mediaItems = [
    {
        title: "I wasted 6 hours reading a repo...",
        description: "How RepoMind solves the 80% of developer time wasted on building context manually.",
        type: "Article",
        platform: "Medium",
        url: "https://medium.com/@pieisnot22by7/i-wasted-6-hours-reading-a-repo-even-after-having-claude-max-80b0be4a9ca6",
        icon: <BookOpen className="w-5 h-5 text-emerald-400" />,
        color: "emerald",
    },
    {
        title: "Official Demo: RepoMind Workflow",
        description: "Watch how to go from a GitHub URL to a full architectural map and security report in seconds.",
        type: "Video",
        platform: "YouTube",
        url: "https://www.youtube.com/watch?v=3f66xlgpjw0",
        icon: <Youtube className="w-5 h-5 text-red-500" />,
        color: "red",
    },
];

export default function MediaShowcase() {
    return (
        <section className="py-24 px-6 relative z-10 w-full bg-zinc-950 border-t border-white/5">
            <div className="max-w-7xl mx-auto">
                <div className="mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
                        Deep Dives & <span className="text-blue-500">Demos</span>
                    </h2>
                    <p className="text-zinc-400 text-lg max-w-2xl">
                        Explore the stories and technical deep dives behind RepoMind&apos;s creation.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {mediaItems.map((item, idx) => (
                        <motion.a
                            key={idx}
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: idx * 0.1 }}
                            className="group relative bg-zinc-900/40 border border-zinc-800 rounded-3xl p-8 hover:bg-zinc-900/60 transition-all hover:border-zinc-700 overflow-hidden"
                        >
                            <div className="flex flex-col h-full">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className={`p-2.5 rounded-xl bg-${item.color}-500/10`}>
                                        {item.icon}
                                    </div>
                                    <span className="text-sm font-bold text-zinc-500 uppercase tracking-widest">
                                        {item.platform} {item.type}
                                    </span>
                                </div>
                                
                                <h3 className="text-2xl font-bold text-white mb-4 group-hover:text-blue-400 transition-colors">
                                    {item.title}
                                </h3>
                                <p className="text-zinc-400 leading-relaxed mb-8 flex-1">
                                    {item.description}
                                </p>

                                <div className="flex items-center gap-2 text-sm font-bold text-white group-hover:translate-x-1 transition-transform">
                                    Read more <ArrowRight size={16} />
                                </div>
                            </div>
                        </motion.a>
                    ))}
                </div>
            </div>
        </section>
    );
}
