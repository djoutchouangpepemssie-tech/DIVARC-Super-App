import './globals.css'
import { Providers } from './providers'

export const metadata = {
  title: 'DIVARC — La super-app européenne',
  description: 'Paiement, messagerie, assistant IA, mini-apps et social vidéo. Conforme RGPD/DMA, centrée sur la confiance.',
  manifest: '/manifest.json',
  applicationName: 'DIVARC',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'DIVARC',
  },
}

export const viewport = {
  themeColor: '#FAF9F4',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({ children }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#FAF9F4" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#0E1020" media="(prefers-color-scheme: dark)" />
        <script dangerouslySetInnerHTML={{__html:'window.addEventListener("error",function(e){if(e.error instanceof DOMException&&e.error.name==="DataCloneError"&&e.message&&e.message.includes("PerformanceServerTiming")){e.stopImmediatePropagation();e.preventDefault()}},true);'}} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
