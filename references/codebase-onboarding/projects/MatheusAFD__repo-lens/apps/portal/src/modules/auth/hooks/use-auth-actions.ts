import { authClient } from '@/lib/auth-client'
import { useRouter } from '@tanstack/react-router'
import type { SignInRequest, SignUpRequest } from '../schemas/auth.schema'

export function useAuthActions() {
  const router = useRouter()

  async function signIn(data: SignInRequest) {
    const { error } = await authClient.signIn.email(data)
    if (error) return error.message ?? 'Invalid credentials'
    await router.navigate({ to: '/dashboard' })

    return null
  }

  async function signUp(data: SignUpRequest) {
    const { error } = await authClient.signUp.email(data)
    if (error) return error.message ?? 'Could not create account'
    await router.navigate({ to: '/dashboard' })

    return null
  }

  async function signInWithGithub() {
    await authClient.signIn.social({
      provider: 'github',
      callbackURL: `${window.location.origin}/dashboard`,
    })
  }

  async function signOut() {
    await authClient.signOut()
    await router.navigate({ to: '/' })
  }

  return { signIn, signUp, signInWithGithub, signOut }
}
