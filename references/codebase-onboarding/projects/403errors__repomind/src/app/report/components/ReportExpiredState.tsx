import Link from "next/link";

interface ReportExpiredStateProps {
    owner?: string;
    repo?: string;
    expiresAt?: Date | number | string;
}

function formatExpiration(expiresAt?: Date | number | string): string | null {
    if (!expiresAt) return null;
    const date = expiresAt instanceof Date ? expiresAt : new Date(expiresAt);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleString();
}

export function ReportExpiredState({ owner, repo, expiresAt }: ReportExpiredStateProps) {
    const formattedExpiry = formatExpiration(expiresAt);
    const rerunHref = owner && repo
        ? `/chat?q=${encodeURIComponent(`${owner}/${repo}`)}`
        : "/";

    return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
            <div className="max-w-lg w-full rounded-2xl border border-white/10 bg-zinc-900 p-8 space-y-4">
                <h1 className="text-2xl font-semibold">Report Outdated</h1>
                <p className="text-zinc-300">
                    This report is no longer current. Security reports expire after 7 days. Run a fresh scan in Repo Chat to regenerate it.
                </p>
                {formattedExpiry && (
                    <p className="text-sm text-zinc-500">
                        Expired at: {formattedExpiry}
                    </p>
                )}
                <div className="flex items-center gap-2">
                    <Link
                        href={rerunHref}
                        className="inline-flex items-center px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 transition-colors text-sm font-medium"
                    >
                        Rescan in Repo Chat
                    </Link>
                    <Link
                        href="/"
                        className="inline-flex items-center px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors text-sm"
                    >
                        Back to Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
