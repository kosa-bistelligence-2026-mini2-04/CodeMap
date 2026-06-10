import { authClient } from '@/lib/auth-client'
import { SignUpForm } from '@/modules/auth/components/register-form'
import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/auth/sign-up')({
  beforeLoad: async () => {
    const { data: session } = await authClient.getSession()
    if (session) throw redirect({ to: '/dashboard' })
  },
  component: SignUpPage,
})

function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <SignUpForm />
    </div>
  )
}
