"use client";

import { motion } from "framer-motion";
import { Youtube, ExternalLink } from "lucide-react";

const mentions = [
    {
        name: "StartupAsRadar",
        url: "https://www.startupasradar.com/startup/3648",
        label: "Featured Startup",
    },
    {
        name: "BuiltAtLightSpeed",
        url: "https://www.builtatlightspeed.com/theme/403errors-repomind",
        label: "Featured Theme",
    },
    {
        name: "Dev Spotlight",
        url: "https://youtu.be/wu3522-is9w?t=43&si=B1iUbB9Yekss7eTF",
        icon: <Youtube className="w-5 h-5" />,
        label: "YouTube Mention",
    },
];

export default function FeaturedIn() {
    return (
        <section className="py-12 bg-black/50 border-y border-white/5 relative z-10 w-full">
            <div className="max-w-7xl mx-auto px-6">
                <p className="text-center text-zinc-500 text-xs font-bold uppercase tracking-[0.3em] mb-10">
                    As Seen On & Featured In
                </p>
                <div className="flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
                    {mentions.map((item) => (
                        <a
                            key={item.name}
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group flex flex-col items-center gap-2 transition-transform hover:scale-105"
                        >
                            <div className="flex items-center gap-2">
                                {item.icon}
                                <span className="text-xl md:text-2xl font-bold tracking-tight text-white group-hover:text-blue-400 transition-colors">
                                    {item.name}
                                </span>
                            </div>
                            <span className="text-[10px] font-medium text-zinc-500 group-hover:text-zinc-400 flex items-center gap-1">
                                {item.label} <ExternalLink size={10} />
                            </span>
                        </a>
                    ))}
                </div>
            </div>
        </section>
    );
}
