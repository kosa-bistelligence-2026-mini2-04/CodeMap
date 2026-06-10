import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/db";
import { ANON_COOKIE_NAME, getAnonymousActorId } from "@/lib/actor-id";
import { getInvalidSessionApiError, getSessionAuthState, getSessionUserId } from "@/lib/session-guard";

type CreateRunBody = {
    scope: "repo" | "profile";
    owner?: string | null;
    repo?: string | null;
    username?: string | null;
    clientRequestId: string;
};

function resolveConversationKey(body: CreateRunBody): { conversationKey: string; owner: string | null; repo: string | null; username: string | null } | null {
    if (body.scope === "repo") {
        const owner = typeof body.owner === "string" ? body.owner : null;
        const repo = typeof body.repo === "string" ? body.repo : null;
        if (!owner || !repo) return null;
        return { conversationKey: `repo:${owner}:${repo}`, owner, repo, username: null };
    }

    const username = typeof body.username === "string" ? body.username : null;
    if (!username) return null;
    return { conversationKey: `profile:${username}`, owner: null, repo: null, username };
}

export async function POST(req: NextRequest) {
    const session = await auth();
    const authState = getSessionAuthState(session);
    if (authState === "invalid") {
        return NextResponse.json(getInvalidSessionApiError(), { status: 401 });
    }

    const userId = getSessionUserId(session);
    const anonCookieId = req.cookies.get(ANON_COOKIE_NAME)?.value ?? null;
    const actorId = userId ?? getAnonymousActorId(req.headers, anonCookieId);

    const body = (await req.json()) as Partial<CreateRunBody>;
    const scope = body.scope;
    const clientRequestId = typeof body.clientRequestId === "string" ? body.clientRequestId : "";
    if ((scope !== "repo" && scope !== "profile") || !clientRequestId.trim()) {
        return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
    }

    const resolved = resolveConversationKey({
        scope,
        owner: body.owner ?? null,
        repo: body.repo ?? null,
        username: body.username ?? null,
        clientRequestId,
    });
    if (!resolved) {
        return NextResponse.json({ error: "Missing conversation parameters" }, { status: 400 });
    }

    const existing = await prisma.chatRun.findUnique({
        where: {
            actorId_conversationKey_clientRequestId: {
                actorId,
                conversationKey: resolved.conversationKey,
                clientRequestId,
            },
        },
        select: { id: true, status: true, partialText: true, finalText: true },
    });

    if (existing) {
        return NextResponse.json({
            runId: existing.id,
            status: existing.status,
            partialText: existing.partialText,
            finalText: existing.finalText,
        });
    }

    const run = await prisma.chatRun.create({
        data: {
            actorId,
            userId: userId ?? null,
            conversationKey: resolved.conversationKey,
            scope,
            owner: resolved.owner,
            repo: resolved.repo,
            username: resolved.username,
            clientRequestId,
            status: "RUNNING",
            partialText: "",
        },
        select: { id: true },
    });

    return NextResponse.json({ runId: run.id, status: "RUNNING", partialText: "", finalText: null });
}

export async function GET(req: NextRequest) {
    const session = await auth();
    const authState = getSessionAuthState(session);
    if (authState === "invalid") {
        return NextResponse.json(getInvalidSessionApiError(), { status: 401 });
    }

    const userId = getSessionUserId(session);
    const anonCookieId = req.cookies.get(ANON_COOKIE_NAME)?.value ?? null;
    const actorId = userId ?? getAnonymousActorId(req.headers, anonCookieId);

    const { searchParams } = new URL(req.url);
    const runId = searchParams.get("runId") ?? "";
    if (!runId.trim()) {
        return NextResponse.json({ error: "Missing runId" }, { status: 400 });
    }

    const run = await prisma.chatRun.findFirst({
        where: { id: runId, actorId },
        select: {
            id: true,
            status: true,
            partialText: true,
            finalText: true,
            errorMessage: true,
            updatedAt: true,
        },
    });

    if (!run) {
        return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    return NextResponse.json({
        runId: run.id,
        status: run.status,
        partialText: run.partialText,
        finalText: run.finalText,
        errorMessage: run.errorMessage,
        updatedAt: run.updatedAt.toISOString(),
    });
}
