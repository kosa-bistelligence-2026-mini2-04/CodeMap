import { ForbiddenException, Injectable, NotFoundException } from '@nestjs/common'
import { eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { session as sessionTable, user as userTable } from '../../../config/database/schema'

interface RevokeSessionParams {
  token: string
}

@Injectable()
export class RevokeSessionUseCase {
  async execute({ token }: RevokeSessionParams) {
    const [target] = await db
      .select({ userId: sessionTable.userId })
      .from(sessionTable)
      .where(eq(sessionTable.token, token))

    if (!target) throw new NotFoundException('Session not found')

    const [targetUser] = await db
      .select({ role: userTable.role })
      .from(userTable)
      .where(eq(userTable.id, target.userId))

    if (targetUser?.role === 'backoffice') {
      throw new ForbiddenException('Cannot revoke session of another admin')
    }

    await db.delete(sessionTable).where(eq(sessionTable.token, token))

    return { success: true }
  }
}
