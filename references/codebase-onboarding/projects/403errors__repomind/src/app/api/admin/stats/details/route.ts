import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/lib/auth";
import { isAdminUser } from "@/lib/admin-auth";
import { getAnalyticsDetails } from "@/lib/analytics";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function parseLimit(value: string | null, fallback: number, max: number): number {
    if (!value) return fallback;
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.max(1, Math.min(max, parsed));
}

function parseCursor(value: string | null): string | null {
    if (!value) return null;
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) return null;
    return String(Math.max(0, parsed));
}

export async function GET(req: NextRequest) {
    try {
        const session = await auth();
        if (!session?.user || !isAdminUser(session)) {
            return NextResponse.json({ error: "Forbidden" }, { status: 403 });
        }

        const visitorLimit = parseLimit(req.nextUrl.searchParams.get("visitorLimit"), 10, 100);
        const visitorCursor = parseCursor(req.nextUrl.searchParams.get("visitorCursor"));
        const loggedInLimit = parseLimit(req.nextUrl.searchParams.get("loggedInLimit"), 10, 200);
        const loggedInCursor = parseCursor(req.nextUrl.searchParams.get("loggedInCursor"));

        const details = await getAnalyticsDetails({
            visitorLimit,
            visitorCursor,
            loggedInLimit,
            loggedInCursor,
            includeSelection: true,
            includeFunnel: true,
            includeFalsePositiveReview: false,
            includeKvHistory: true,
        });

        return NextResponse.json(details);
    } catch (error) {
        console.error("Failed to load admin analytics details:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
