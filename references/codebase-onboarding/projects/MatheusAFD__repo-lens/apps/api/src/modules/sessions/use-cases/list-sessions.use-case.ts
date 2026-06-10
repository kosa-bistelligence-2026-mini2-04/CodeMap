import { Injectable } from '@nestjs/common'
import { desc, gt } from 'drizzle-orm'
import { db } from '../../../config/database'
import { session as sessionTable } from '../../../config/database/schema'

@Injectable()
export class ListSessionsUseCase {
  async execute() {
    return db
      .select()
      .from(sessionTable)
      .where(gt(sessionTable.expiresAt, new Date()))
      .orderBy(desc(sessionTable.createdAt))
  }
}
