'use client'
import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { getToken } from '@/lib/auth'
import ProgressFeed from '@/components/ProgressFeed'

export default function ProgressPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login')
    }
  }, [router])

  const token = typeof window !== 'undefined' ? getToken() : null
  if (!token) {
    return null
  }

  if (!id) return null

  return (
    <div className="min-h-screen bg-brand-black">
      <header className="bg-brand-gray border-b border-brand-lightgray px-6 py-4 flex items-center justify-between">
        <h1 className="text-brand-yellow font-bold text-lg">Mel&apos;s Builders Pro Systems</h1>
        <Link href="/dashboard" className="text-gray-400 hover:text-white text-sm transition">
          ← Back to Dashboard
        </Link>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-10">
        <h2 className="text-2xl font-semibold text-white mb-2">Processing your plans…</h2>
        <p className="text-gray-400 text-sm mb-8">
          Our AI is analysing your PDF. This usually takes 1–3 minutes. You can leave this page — the results will be saved.
        </p>

        <ProgressFeed projectId={id} />
      </main>
    </div>
  )
}
