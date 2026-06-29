import type {
    DocGetJsonResponse,
} from "@/common/types/contracts";
import { getAccessToken } from "@/features/auth/utils/tokenMemory";

const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const DOCS_BASE = `${BASE_PATH}/api/gen/docs`;

function authHeaders(): HeadersInit {
    const token = getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchOnboardingDocJson(
    repoId: string
): Promise<DocGetJsonResponse> {
    const res = await fetch(
        `${DOCS_BASE}/${repoId}?format=json`,
        { headers: authHeaders() }
    );
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
            (body as { message?: string }).message ??
            `docs fetch error: ${res.status}`
        );
    }
    return res.json() as Promise<DocGetJsonResponse>;
}

export function buildMarkdownDownloadUrl(repoId: string): string {
    return `${DOCS_BASE}/${repoId}/download?format=md`;
}
