import { authClient } from '@/lib/auth-client'
import { SignInForm } from '@/modules/auth/components/login-form'
import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/auth/sign-in')({
  beforeLoad: async () => {
    const { data: session } = await authClient.getSession()
    if (session) throw redirect({ to: '/dashboard' })
  },
  component: SignInPage,
})

function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <SignInForm />
    </div>
  )
}
