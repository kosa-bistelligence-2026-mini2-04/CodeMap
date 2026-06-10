import { Injectable } from '@nestjs/common'
import { and, eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { account as accountTable } from '../../../config/database/schema'

interface GetTokenParams {
  userId: string
}

@Injectable()
export class GetTokenUseCase {
  async execute({ userId }: GetTokenParams): Promise<string | null> {
    const [row] = await db
      .select({ accessToken: accountTable.accessToken })
      .from(accountTable)
      .where(and(eq(accountTable.userId, userId), eq(accountTable.providerId, 'github')))

    return row?.accessToken ?? null
  }
}
