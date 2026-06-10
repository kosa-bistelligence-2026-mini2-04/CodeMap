import { ForbiddenException, NotFoundException } from '@nestjs/common'

interface AssertOwnerArgs<T extends { userId: string }> {
  row: T | undefined
  userId: string
  notFoundMessage?: string
  forbiddenMessage?: string
}

export function assertOwner<T extends { userId: string }>({
  row,
  userId,
  notFoundMessage = 'Resource not found',
  forbiddenMessage = 'Resource does not belong to user',
}: AssertOwnerArgs<T>): T {
  if (!row) throw new NotFoundException(notFoundMessage)
  if (row.userId !== userId) throw new ForbiddenException(forbiddenMessage)
  return row
}
