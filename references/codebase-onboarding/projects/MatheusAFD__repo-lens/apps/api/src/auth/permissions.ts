import { createAccessControl } from 'better-auth/plugins/access'

const statement = {
  portal: ['access'],
  backoffice: ['access'],
} as const

export const ac = createAccessControl(statement)

export const portalRole = ac.newRole({
  portal: ['access'],
})

export const backofficeRole = ac.newRole({
  backoffice: ['access'],
  portal: ['access'],
})
