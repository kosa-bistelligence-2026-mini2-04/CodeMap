import { randomUUID } from 'node:crypto'
import { relations } from 'drizzle-orm'
import { boolean, index, integer, pgTable, text, timestamp } from 'drizzle-orm/pg-core'

export const user = pgTable('user', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  email: text('email').notNull().unique(),
  emailVerified: boolean('email_verified').default(false).notNull(),
  image: text('image'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at')
    .defaultNow()
    .$onUpdate(() => new Date())
    .notNull(),
  role: text('role'),
  banned: boolean('banned').default(false),
  banReason: text('ban_reason'),
  banExpires: timestamp('ban_expires'),
})

export const session = pgTable(
  'session',
  {
    id: text('id').primaryKey(),
    expiresAt: timestamp('expires_at').notNull(),
    token: text('token').notNull().unique(),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at')
      .$onUpdate(() => new Date())
      .notNull(),
    ipAddress: text('ip_address'),
    userAgent: text('user_agent'),
    userId: text('user_id')
      .notNull()
      .references(() => user.id, { onDelete: 'cascade' }),
    impersonatedBy: text('impersonated_by'),
  },
  (table) => [index('session_userId_idx').on(table.userId)],
)

export const account = pgTable(
  'account',
  {
    id: text('id').primaryKey(),
    accountId: text('account_id').notNull(),
    providerId: text('provider_id').notNull(),
    userId: text('user_id')
      .notNull()
      .references(() => user.id, { onDelete: 'cascade' }),
    accessToken: text('access_token'),
    refreshToken: text('refresh_token'),
    idToken: text('id_token'),
    accessTokenExpiresAt: timestamp('access_token_expires_at'),
    refreshTokenExpiresAt: timestamp('refresh_token_expires_at'),
    scope: text('scope'),
    password: text('password'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at')
      .$onUpdate(() => new Date())
      .notNull(),
  },
  (table) => [index('account_userId_idx').on(table.userId)],
)

export const verification = pgTable(
  'verification',
  {
    id: text('id').primaryKey(),
    identifier: text('identifier').notNull(),
    value: text('value').notNull(),
    expiresAt: timestamp('expires_at').notNull(),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at')
      .defaultNow()
      .$onUpdate(() => new Date())
      .notNull(),
  },
  (table) => [index('verification_identifier_idx').on(table.identifier)],
)

export const userRelations = relations(user, ({ many }) => ({
  sessions: many(session),
  accounts: many(account),
  repositories: many(repository),
}))

export const sessionRelations = relations(session, ({ one }) => ({
  user: one(user, {
    fields: [session.userId],
    references: [user.id],
  }),
}))

export const accountRelations = relations(account, ({ one }) => ({
  user: one(user, {
    fields: [account.userId],
    references: [user.id],
  }),
}))

export const repository = pgTable(
  'repository',
  {
    id: text('id')
      .primaryKey()
      .$defaultFn(() => randomUUID()),
    userId: text('user_id')
      .notNull()
      .references(() => user.id, { onDelete: 'cascade' }),
    githubRepoId: text('github_repo_id').notNull(),
    owner: text('owner').notNull(),
    name: text('name').notNull(),
    fullName: text('full_name').notNull(),
    description: text('description'),
    language: text('language'),
    isPrivate: boolean('is_private').default(false).notNull(),
    htmlUrl: text('html_url').notNull(),
    codeAreas: text('code_areas'),
    codeAreasComputedAt: timestamp('code_areas_computed_at'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at')
      .defaultNow()
      .$onUpdate(() => new Date())
      .notNull(),
  },
  (table) => [
    index('repository_userId_idx').on(table.userId),
    index('repository_fullName_idx').on(table.fullName),
  ],
)

export const analysis = pgTable(
  'analysis',
  {
    id: text('id')
      .primaryKey()
      .$defaultFn(() => randomUUID()),
    repositoryId: text('repository_id')
      .notNull()
      .references(() => repository.id, { onDelete: 'cascade' }),
    userId: text('user_id')
      .notNull()
      .references(() => user.id, { onDelete: 'cascade' }),
    previousAnalysisId: text('previous_analysis_id'),
    status: text('status').notNull().default('running'),
    result: text('result'),
    errorMessage: text('error_message'),
    inputTokens: integer('input_tokens'),
    outputTokens: integer('output_tokens'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    completedAt: timestamp('completed_at'),
  },
  (table) => [
    index('analysis_repositoryId_idx').on(table.repositoryId),
    index('analysis_userId_idx').on(table.userId),
  ],
)

export const repositoryRelations = relations(repository, ({ one, many }) => ({
  user: one(user, { fields: [repository.userId], references: [user.id] }),
  analyses: many(analysis),
  chats: many(chat),
}))

export const analysisRelations = relations(analysis, ({ one, many }) => ({
  repository: one(repository, { fields: [analysis.repositoryId], references: [repository.id] }),
  user: one(user, { fields: [analysis.userId], references: [user.id] }),
  questions: many(analysisQuestion),
}))

export const analysisQuestion = pgTable(
  'analysis_question',
  {
    id: text('id')
      .primaryKey()
      .$defaultFn(() => randomUUID()),
    analysisId: text('analysis_id')
      .notNull()
      .references(() => analysis.id, { onDelete: 'cascade' }),
    userId: text('user_id')
      .notNull()
      .references(() => user.id, { onDelete: 'cascade' }),
    question: text('question').notNull(),
    answer: text('answer'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
  },
  (table) => [index('analysis_question_analysisId_idx').on(table.analysisId)],
)

export const analysisQuestionRelations = relations(analysisQuestion, ({ one }) => ({
  analysis: one(analysis, { fields: [analysisQuestion.analysisId], references: [analysis.id] }),
  user: one(user, { fields: [analysisQuestion.userId], references: [user.id] }),
}))

export const chat = pgTable(
  'chat',
  {
    id: text('id')
      .primaryKey()
      .$defaultFn(() => randomUUID()),
    repositoryId: text('repository_id')
      .notNull()
      .references(() => repository.id, { onDelete: 'cascade' }),
    userId: text('user_id')
      .notNull()
      .references(() => user.id, { onDelete: 'cascade' }),
    title: text('title').notNull().default('New conversation'),
    bootstrapContext: text('bootstrap_context'),
    lastMessageAt: timestamp('last_message_at').defaultNow().notNull(),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at')
      .defaultNow()
      .$onUpdate(() => new Date())
      .notNull(),
  },
  (table) => [
    index('chat_repositoryId_idx').on(table.repositoryId),
    index('chat_userId_idx').on(table.userId),
    index('chat_lastMessageAt_idx').on(table.lastMessageAt),
  ],
)

export const chatMessage = pgTable(
  'chat_message',
  {
    id: text('id')
      .primaryKey()
      .$defaultFn(() => randomUUID()),
    chatId: text('chat_id')
      .notNull()
      .references(() => chat.id, { onDelete: 'cascade' }),
    role: text('role').notNull(),
    content: text('content').notNull(),
    status: text('status').notNull().default('complete'),
    errorMessage: text('error_message'),
    inputTokens: integer('input_tokens'),
    outputTokens: integer('output_tokens'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
  },
  (table) => [
    index('chat_message_chatId_idx').on(table.chatId),
    index('chat_message_createdAt_idx').on(table.createdAt),
  ],
)

export const chatRelations = relations(chat, ({ one, many }) => ({
  repository: one(repository, { fields: [chat.repositoryId], references: [repository.id] }),
  user: one(user, { fields: [chat.userId], references: [user.id] }),
  messages: many(chatMessage),
}))

export const chatMessageRelations = relations(chatMessage, ({ one }) => ({
  chat: one(chat, { fields: [chatMessage.chatId], references: [chat.id] }),
}))
