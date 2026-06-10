import { Suspense } from "react";
import type { Metadata } from "next";
import { createSeoMetadata } from "@/lib/seo";
import ChatPageClient from "./ChatPageClient";

const CHAT_ROBOTS: NonNullable<Metadata["robots"]> = {
    index: false,
    follow: true,
    googleBot: {
        index: false,
        follow: true,
        "max-video-preview": -1,
        "max-image-preview": "large",
        "max-snippet": -1,
    },
};

const staticMetadata = createSeoMetadata({
    title: "Chat",
    description: "Paste a GitHub repository or developer profile to analyze it with RepoMind.",
    canonical: "/chat",
    ogTitle: "RepoMind chat",
    ogDescription: "Chat with GitHub repositories and developer profiles using Agentic CAG.",
});
staticMetadata.robots = CHAT_ROBOTS;

export const metadata: Metadata = staticMetadata;

export default function ChatPage() {
    return (
        <Suspense fallback={null}>
            <ChatPageClient />
        </Suspense>
    );
}
