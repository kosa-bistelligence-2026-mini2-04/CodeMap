export const USER_ROLES = {
  Portal: 'portal',
  Backoffice: 'backoffice',
} as const

export type UserRole = (typeof USER_ROLES)[keyof typeof USER_ROLES]
