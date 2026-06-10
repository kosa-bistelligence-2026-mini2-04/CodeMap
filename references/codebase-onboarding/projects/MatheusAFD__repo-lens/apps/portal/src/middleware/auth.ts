import { authClient } from '@/lib/auth-client'
import { redirect } from '@tanstack/react-router'
import { createMiddleware } from '@tanstack/react-start'
import { getRequestHeaders } from '@tanstack/react-start/server'

export const authMiddleware = createMiddleware().server(async ({ next }) => {
  const { data: session } = await authClient.getSession({
    fetchOptions: { headers: getRequestHeaders() },
  })

  if (!session) {
    throw redirect({ to: '/auth/sign-in' })
  }

  return next({ context: { session } })
})
