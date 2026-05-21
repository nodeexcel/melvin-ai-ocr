import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: "Mel's Builders Pro Systems",
  description: 'AI Construction Estimator',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-brand-black text-white min-h-screen">{children}</body>
    </html>
  )
}
