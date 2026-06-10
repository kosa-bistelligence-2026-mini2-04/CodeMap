"use client";

import { useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ProfileLoader } from "@/components/ProfileLoader";
import { RepoLoader } from "@/components/RepoLoader";
import { normalizeGitHubInput } from "@/lib/utils";

export default function ChatPageClient() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const rawQuery = searchParams.get("q") ?? "";
    const prompt = searchParams.get("prompt") ?? undefined;
    const query = useMemo(() => normalizeGitHubInput(rawQuery), [rawQuery]);

    useEffect(() => {
        if (!query) {
            router.replace("/");
        }
    }, [query, router]);

    if (!query) {
        return null;
    }

    if (!query.includes("/")) {
        return <ProfileLoader username={query} />;
    }

    return <RepoLoader query={query} initialPrompt={prompt} />;
}
