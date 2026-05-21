'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { listProjects, deleteProject } from '@/lib/api'
import { isAuthenticated, clearToken } from '@/lib/auth'
import ProjectCard from '@/components/ProjectCard'
import type { ProjectOut } from '@/types'

export default function DashboardPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<ProjectOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) { router.replace('/login'); return }
    listProjects()
      .then(setProjects)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [router])

  async function handleDelete(id: string) {
    if (!confirm('Delete this project?')) return
    await deleteProject(id)
    setProjects(p => p.filter(x => x.id !== id))
  }

  function handleLogout() {
    clearToken()
    router.replace('/login')
  }

  return (
    <div className="min-h-screen bg-brand-black">
      <header className="bg-brand-gray border-b border-brand-lightgray px-6 py-4 flex items-center justify-between">
        <h1 className="text-brand-yellow font-bold text-lg">Mel&apos;s Builders Pro Systems</h1>
        <div className="flex items-center gap-4">
          <Link href="/upload" className="bg-brand-yellow text-brand-black font-bold px-4 py-2 rounded text-sm hover:opacity-90 transition">
            + New Estimate
          </Link>
          <button onClick={handleLogout} className="text-gray-400 hover:text-white text-sm transition">
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <h2 className="text-xl font-semibold text-white mb-4">Project History</h2>

        {loading && <p className="text-gray-400">Loading...</p>}
        {error && <p className="text-red-400">{error}</p>}

        {!loading && projects.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            <p className="text-lg">No estimates yet.</p>
            <Link href="/upload" className="text-brand-yellow underline mt-2 inline-block">
              Upload your first plan set →
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {projects.map(p => (
            <ProjectCard key={p.id} project={p} onDelete={handleDelete} />
          ))}
        </div>
      </main>
    </div>
  )
}
