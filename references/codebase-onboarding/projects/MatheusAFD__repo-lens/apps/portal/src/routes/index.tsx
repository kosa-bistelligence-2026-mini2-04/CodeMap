import { authClient } from '@/lib/auth-client'
import { ThemeSelector } from '@/common/components/theme-selector'
import { useAuthActions } from '@/modules/auth/hooks/use-auth-actions'
import { Button, buttonVariants } from '@repo/ui/components/button'
import { Link, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: LandingPage,
})

function LandingPage() {
  const { signInWithGithub } = useAuthActions()
  const { data: session } = authClient.useSession()

  const isLoggedIn = !!session

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border/40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-foreground flex items-center justify-center">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="w-3.5 h-3.5 stroke-background"
                fill="none"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <span className="text-sm font-semibold tracking-tight">RepoLens</span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeSelector />
            {isLoggedIn ? (
              <Link to="/dashboard" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
                Dashboard
              </Link>
            ) : (
              <Button variant="ghost" size="sm" onClick={signInWithGithub} className="gap-2">
                <GithubIcon />
                Sign in
              </Button>
            )}
          </div>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <div className="max-w-2xl space-y-6">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-border/60 bg-muted/40 text-xs text-muted-foreground">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Powered by Claude AI
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-foreground leading-tight">
            Understand any <span className="text-muted-foreground">codebase</span>
            <br />
            in minutes
          </h1>

          <p className="text-base sm:text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
            AI-powered repository analysis. Get a plain-language summary, security audit, dependency
            health, and a prioritized action plan — streamed live as Claude reads your code.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            {isLoggedIn ? (
              <Link
                to="/dashboard"
                className={`${buttonVariants({ size: 'lg' })} h-11 px-6 text-sm font-medium`}
              >
                Go to Dashboard
              </Link>
            ) : (
              <Button
                size="lg"
                onClick={signInWithGithub}
                className="gap-2 h-11 px-6 text-sm font-medium"
              >
                <GithubIcon />
                Connect with GitHub
              </Button>
            )}
            <p className="text-xs text-muted-foreground">
              Free to use · Runs locally · No data stored
            </p>
          </div>
        </div>

        <div className="mt-20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl w-full">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="rounded-xl border border-border/60 bg-card p-5 text-left space-y-2 hover:border-border transition-colors"
            >
              <div className="text-lg">{feature.icon}</div>
              <h3 className="text-sm font-semibold text-foreground">{feature.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="px-6 py-4 text-center text-xs text-muted-foreground border-t border-border/40">
        Your API keys never leave your server.
      </footer>
    </div>
  )
}

function GithubIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="w-4 h-4 fill-current">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}

const FEATURES = [
  {
    icon: '📋',
    title: 'Executive Summary',
    description: 'Plain-language overview any non-technical stakeholder can understand.',
  },
  {
    icon: '🔒',
    title: 'Security Audit',
    description: 'OWASP Top 10 focused scan with severity levels and an A–F health grade.',
  },
  {
    icon: '📦',
    title: 'Dependency Health',
    description: 'Outdated and vulnerable packages surfaced with actionable update plans.',
  },
  {
    icon: '✅',
    title: 'Next Steps',
    description: 'Ranked recommendations ordered by impact so you always know what to tackle.',
  },
]
