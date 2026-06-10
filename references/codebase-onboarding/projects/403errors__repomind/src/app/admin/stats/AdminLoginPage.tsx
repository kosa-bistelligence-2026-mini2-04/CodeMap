export default function AdminLoginPage() {
    return (
        <div className="min-h-[60vh] flex items-center justify-center px-6">
            <div className="max-w-md w-full rounded-2xl border border-white/10 bg-zinc-950/50 p-6 text-center">
                <h1 className="text-lg font-semibold text-white">Admin access required</h1>
                <p className="mt-2 text-sm text-zinc-400">
                    Please sign in with the configured admin GitHub account to view analytics.
                </p>
            </div>
        </div>
    );
}

