import type { Config } from 'drizzle-kit'

export default {
  schema: './src/config/database/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: {
    // biome-ignore lint/style/noNonNullAssertion: <explanation>
    url: process.env.DATABASE_URL!,
  },
} satisfies Config
