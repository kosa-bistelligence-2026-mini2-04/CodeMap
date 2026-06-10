import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Analytics } from '@vercel/analytics/react'
import { PostHogProvider } from 'posthog-js/react'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PostHogProvider
      apiKey={import.meta.env.VITE_PUBLIC_POSTHOG_KEY}
      options={{
        api_host: 'https://us.i.posthog.com',
        debug: import.meta.env.MODE === "development",
      }}
    >
      <App />
      <Analytics />
    </PostHogProvider>
  </StrictMode>,
)
