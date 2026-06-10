import { authMiddleware } from '@/middleware/auth'
import { Outlet, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_authed')({
  component: AuthedLayout,
  server: {
    middleware: [authMiddleware],
  },
})

function AuthedLayout() {
  return <Outlet />
}
