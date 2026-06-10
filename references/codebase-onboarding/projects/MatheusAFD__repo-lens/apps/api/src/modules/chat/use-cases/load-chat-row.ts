import { eq } from 'drizzle-orm'
import { assertOwner } from '../../../common/guards/ownership'
import { db } from '../../../config/database'
import { chat } from '../../../config/database/schema'

export async function loadChatRow(
  chatId: string,
  userId: string,
): Promise<typeof chat.$inferSelect> {
  const [row] = await db.select().from(chat).where(eq(chat.id, chatId))
  return assertOwner({
    row,
    userId,
    notFoundMessage: 'Chat not found',
    forbiddenMessage: 'Chat does not belong to user',
  })
}
