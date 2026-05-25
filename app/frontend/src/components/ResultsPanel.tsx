'use client'
import { getToken } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8037'

interface ResultsPanelProps {
  projectId: string
  projectName: string
  rawJson: Record<string, unknown> | null
  reportPdfUrl: string | null
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="text-brand-yellow font-semibold text-sm uppercase tracking-wider mb-3">
      {title}
    </h3>
  )
}

function toTitleCase(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function InlineValue({ v }: { v: unknown }) {
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="text-gray-500 text-sm">None</span>
    return (
      <details className="text-right">
        <summary className="text-brand-yellow text-sm cursor-pointer hover:text-yellow-300 select-none list-none">
          {v.length} item{v.length !== 1 ? 's' : ''} ▸
        </summary>
        <ul className="mt-2 space-y-1 text-left">
          {v.map((item, i) => (
            <li key={i} className="text-gray-300 text-xs bg-brand-black rounded px-2 py-1 font-mono whitespace-pre-wrap break-all">
              {typeof item === 'object' && item !== null ? JSON.stringify(item, null, 2) : String(item)}
            </li>
          ))}
        </ul>
      </details>
    )
  }
  if (v !== null && typeof v === 'object') {
    const entries = Object.entries(v as Record<string, unknown>)
    if (entries.length === 0) return <span className="text-gray-500 text-sm">None</span>
    return (
      <details className="text-right">
        <summary className="text-brand-yellow text-sm cursor-pointer hover:text-yellow-300 select-none list-none">
          {entries.length} field{entries.length !== 1 ? 's' : ''} ▸
        </summary>
        <ul className="mt-2 space-y-1 text-left">
          {entries.map(([k, val]) => (
            <li key={k} className="text-gray-300 text-xs bg-brand-black rounded px-2 py-1 font-mono whitespace-pre-wrap break-all">
              {k}: {String(val ?? '')}
            </li>
          ))}
        </ul>
      </details>
    )
  }
  return <span className="text-white text-sm font-mono break-all">{String(v ?? '')}</span>
}

function DynamicSection({ sectionKey, value }: { sectionKey: string; value: unknown }) {
  const title = toTitleCase(sectionKey)

  if (Array.isArray(value)) {
    return (
      <section className="bg-brand-gray rounded-lg p-5">
        <SectionHeader title={title} />
        {value.length === 0 ? (
          <span className="text-gray-500 text-sm">None</span>
        ) : (
          <details className="mt-1">
            <summary className="text-brand-yellow text-sm cursor-pointer hover:text-yellow-300 select-none">
              {value.length} item{value.length !== 1 ? 's' : ''}
            </summary>
            <ul className="mt-2 space-y-1 pl-3">
              {value.map((item, i) => (
                <li key={i} className="text-gray-300 text-xs bg-brand-black rounded px-2 py-1 font-mono whitespace-pre-wrap break-all">
                  {typeof item === 'object' && item !== null ? JSON.stringify(item, null, 2) : String(item)}
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>
    )
  }

  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    return (
      <section className="bg-brand-gray rounded-lg p-5">
        <SectionHeader title={title} />
        {entries.length === 0 ? (
          <span className="text-gray-500 text-sm">None</span>
        ) : (
          <div>
            {entries.map(([k, v]) => (
              <div
                key={k}
                className="flex justify-between items-start py-1.5 border-b border-brand-lightgray last:border-0 gap-4"
              >
                <span className="text-gray-400 text-sm shrink-0">{toTitleCase(k)}</span>
                <InlineValue v={v} />
              </div>
            ))}
          </div>
        )}
      </section>
    )
  }

  // Primitive
  return (
    <section className="bg-brand-gray rounded-lg p-5">
      <SectionHeader title={title} />
      <span className="text-white text-sm">{String(value ?? '')}</span>
    </section>
  )
}

export default function ResultsPanel({
  projectId,
  projectName,
  rawJson,
  reportPdfUrl,
}: ResultsPanelProps) {
  async function handleDownload() {
    if (!reportPdfUrl) return
    const token = getToken()
    if (!token) return
    const response = await fetch(`${API}${reportPdfUrl}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) return
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'estimate.pdf'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold text-white">{projectName}</h2>
          <p className="text-gray-400 text-sm mt-1">Analysis complete</p>
        </div>
        {reportPdfUrl && (
          <button
            onClick={() => { void handleDownload() }}
            className="bg-brand-yellow text-brand-black font-semibold px-5 py-2.5 rounded-lg hover:bg-yellow-400 transition text-sm shrink-0"
          >
            Download PDF Report
          </button>
        )}
      </div>

      {!rawJson ? (
        <div className="bg-brand-gray rounded-lg p-6 text-center text-gray-400">
          No results available
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(rawJson).map(([key, value]) => (
            <DynamicSection key={key} sectionKey={key} value={value} />
          ))}
        </div>
      )}
    </div>
  )
}
