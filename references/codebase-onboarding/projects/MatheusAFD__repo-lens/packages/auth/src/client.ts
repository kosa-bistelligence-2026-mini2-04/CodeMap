import { createAuthClient } from 'better-auth/client'

export type { Session, User } from 'better-auth/types'

/**
 * Creates a Better Auth client configured to communicate with the backend.
 * Import `inferAdditionalFields` and React hooks in each app's own auth-client file.
 *
 * @example
 * // apps/portal/src/lib/auth-client.ts
 * import { createAuthClient } from 'better-auth/react'
 * import { inferAdditionalFields } from 'better-auth/client/plugins'
 * import type { auth } from '@repo/auth/types'
 *
 * export const authClient = createAuthClient({
 *   baseURL: import.meta.env.VITE_API_URL,
 *   plugins: [inferAdditionalFields<typeof auth>()],
 * })
 */
export function createClient(options: { baseURL: string }) {
  return createAuthClient({
    baseURL: options.baseURL,
  })
}
