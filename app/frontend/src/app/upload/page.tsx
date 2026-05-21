'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { uploadProject } from '@/lib/api'
import UploadZone from '@/components/UploadZone'

export default function UploadPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  function handleFile(f: File) {
    setFile(f)
    if (!name) setName(f.name.replace(/\.pdf$/i, ''))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const project = await uploadProject(name, file)
      router.push(`/projects/${project.id}/progress`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-brand-black">
      <header className="bg-brand-gray border-b border-brand-lightgray px-6 py-4 flex items-center gap-4">
        <Link href="/dashboard" className="text-gray-400 hover:text-white text-sm">← Dashboard</Link>
        <h1 className="text-brand-yellow font-bold text-lg">New Estimate</h1>
      </header>

      <main className="max-w-xl mx-auto px-4 py-10">
        <form onSubmit={handleSubmit} className="space-y-6">
          <UploadZone onFile={handleFile} />

          {file && (
            <div className="bg-brand-gray rounded p-3 text-sm text-gray-300">
              Selected: <span className="text-white font-medium">{file.name}</span>
              {' '}({(file.size / 1024 / 1024).toFixed(1)} MB)
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Project Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              placeholder="e.g. San Vicente Residence"
              className="w-full bg-brand-black border border-brand-lightgray rounded px-3 py-2 text-white focus:outline-none focus:border-brand-yellow"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={!file || uploading}
            className="w-full bg-brand-yellow text-brand-black font-bold py-3 rounded hover:opacity-90 disabled:opacity-40 transition"
          >
            {uploading ? 'Uploading...' : 'Start Analysis'}
          </button>
        </form>
      </main>
    </div>
  )
}
