import { AppHeader } from '@/common/components/app-header'
import { RepoList } from '@/modules/repos/components/repo-list'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_authed/dashboard')({
  component: DashboardPage,
})

function DashboardPage() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <RepoList />
      </main>
    </div>
  )
}
