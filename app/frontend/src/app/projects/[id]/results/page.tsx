'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { getToken } from '@/lib/auth'
import { getProject } from '@/lib/api'
import ResultsPanel from '@/components/ResultsPanel'
import type { ProjectDetail } from '@/types'

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Sync auth guard — prevents flash
  const token = typeof window !== 'undefined' ? getToken() : null
  if (!token) {
    // Side-effect redirect handled in useEffect; return null immediately
    return null
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  useEffect(() => {
    if (!getToken()) {
      router.replace('/login')
      return
    }
    if (!id) return

    getProject(id)
      .then((p) => {
        setProject(p)
        setLoading(false)
      })
      .catch((err: Error) => {
        setError(err.message)
        setLoading(false)
      })
  }, [id, router])

  return (
    <div className="min-h-screen bg-brand-black">
      <header className="bg-brand-gray border-b border-brand-lightgray px-6 py-4 flex items-center justify-between">
        <h1 className="text-brand-yellow font-bold text-lg">Mel&apos;s Builders Pro Systems</h1>
        <Link href="/dashboard" className="text-gray-400 hover:text-white text-sm transition">
          ← Back to Dashboard
        </Link>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-brand-yellow border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {!loading && error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-6 text-center">
            <p className="text-red-300 text-sm">{error}</p>
            <Link href="/dashboard" className="text-brand-yellow text-sm mt-3 inline-block hover:underline">
              ← Back to Dashboard
            </Link>
          </div>
        )}

        {!loading && !error && project && project.status !== 'done' && (
          <div className="bg-brand-gray rounded-lg p-8 text-center space-y-4">
            <p className="text-white text-lg font-semibold">Analysis not complete yet</p>
            <p className="text-gray-400 text-sm">
              Current status: <span className="text-white font-medium">{project.status}</span>
            </p>
            <Link
              href={`/projects/${id}/progress`}
              className="inline-block bg-brand-yellow text-brand-black font-semibold px-5 py-2.5 rounded-lg hover:bg-yellow-400 transition text-sm"
            >
              View Progress
            </Link>
          </div>
        )}

        {!loading && !error && project && project.status === 'done' && (
          <ResultsPanel
            projectId={id}
            projectName={project.name}
            rawJson={project.raw_json}
            reportPdfUrl={project.report_pdf_url}
          />
        )}
      </main>
    </div>
  )
}
