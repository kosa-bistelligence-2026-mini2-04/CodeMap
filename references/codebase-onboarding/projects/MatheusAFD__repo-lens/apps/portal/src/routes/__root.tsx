import { TanStackDevtools } from '@tanstack/react-devtools'
import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { Toaster } from '@repo/ui/components/sonner'

import appCss from '../styles.css?url'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'RepoLens — AI Repository Analyzer' },
    ],
    links: [{ rel: 'stylesheet', href: appCss }],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <HeadContent />
        <script
          // biome-ignore lint/security/noDangerouslySetInnerHtml: theme init script must run synchronously before first paint to avoid flash
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=document.cookie.match(/repolens-theme=([^;]+)/)?.[1]||localStorage.getItem('repolens-theme');if(t==='light'||(t==='system'&&!window.matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('light');})()`,
          }}
        />
      </head>
      <body>
        {children}
        <Toaster />
        <TanStackDevtools
          config={{ position: 'bottom-right' }}
          plugins={[{ name: 'Tanstack Router', render: <TanStackRouterDevtoolsPanel /> }]}
        />
        <Scripts />
      </body>
    </html>
  )
}
