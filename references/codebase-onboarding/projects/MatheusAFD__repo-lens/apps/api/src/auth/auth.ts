import { betterAuth } from 'better-auth'
import { drizzleAdapter } from 'better-auth/adapters/drizzle'
import { admin } from 'better-auth/plugins'
import { db } from '../config/database'
import * as schema from '../config/database/schema'
import { ac, portalRole, backofficeRole } from './permissions'

export const auth = betterAuth({
  appName: 'RepoLens',
  database: drizzleAdapter(db, {
    provider: 'pg',
    schema,
  }),
  trustedOrigins: process.env.ALLOWED_ORIGINS?.split(',') ?? [
    'http://localhost:3000',
    'http://localhost:3001',
  ],
  session: {
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60,
    },
  },
  emailAndPassword: {
    enabled: true,
  },
  socialProviders: {
    github: {
      // biome-ignore lint/style/noNonNullAssertion: <explanation>
      clientId: process.env.GITHUB_CLIENT_ID!,
      // biome-ignore lint/style/noNonNullAssertion: <explanation>
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      scope: ['read:user', 'public_repo'],
    },
  },
  plugins: [
    admin({
      ac,
      roles: {
        portal: portalRole,
        backoffice: backofficeRole,
      },
      defaultRole: 'portal',
    }),
  ],
})
