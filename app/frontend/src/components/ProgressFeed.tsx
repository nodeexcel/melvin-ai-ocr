'use client'
import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { getToken } from '@/lib/auth'

interface SSEEvent {
  step: string
  message?: string
  progress_pct: number
  status?: string
}

interface ProgressFeedProps {
  projectId: string
}

export default function ProgressFeed({ projectId }: ProgressFeedProps) {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [finalStatus, setFinalStatus] = useState<'done' | 'failed' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setError('Not authenticated')
      return
    }

    const url = `http://localhost:8000/api/projects/${projectId}/stream?token=${encodeURIComponent(token)}`
    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (e) => {
      try {
        const data: SSEEvent = JSON.parse(e.data)
        if (data.step === 'complete') {
          setFinalStatus(data.status === 'done' ? 'done' : 'failed')
          es.close()
        } else {
          setEvents((prev) => [...prev, data])
        }
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = () => {
      setError('Connection lost. Please refresh the page.')
      es.close()
    }

    return () => {
      es.close()
    }
  }, [projectId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events, finalStatus])

  const latestPct = events.length > 0 ? events[events.length - 1].progress_pct : 0

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      {finalStatus === null && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-400">Progress</span>
            <span className="text-sm text-brand-yellow font-mono">{latestPct}%</span>
          </div>
          <div className="w-full bg-brand-lightgray rounded-full h-2">
            <div
              className="bg-brand-yellow h-2 rounded-full transition-all duration-500"
              style={{ width: `${latestPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Event log */}
      <div className="bg-brand-gray rounded-lg p-4 min-h-48 max-h-80 overflow-y-auto font-mono text-sm space-y-1">
        {events.length === 0 && finalStatus === null && (
          <p className="text-gray-500">Waiting for pipeline to start…</p>
        )}
        {events.map((ev, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="text-gray-500 shrink-0 w-8 text-right">{ev.progress_pct}%</span>
            <span className="text-gray-300">
              <span className="text-brand-yellow">[{ev.step}]</span>{' '}
              {ev.message ?? ''}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Spinner while running */}
      {finalStatus === null && !error && (
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <svg
            className="animate-spin h-4 w-4 text-brand-yellow"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Analysing…
        </div>
      )}

      {/* Done */}
      {finalStatus === 'done' && (
        <div className="rounded-lg border border-green-600 bg-green-950 p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-400 font-semibold">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Analysis complete!
          </div>
          <Link
            href={`/projects/${projectId}/results`}
            className="bg-brand-yellow text-brand-black font-bold px-4 py-2 rounded text-sm hover:opacity-90 transition"
          >
            View Results →
          </Link>
        </div>
      )}

      {/* Failed */}
      {finalStatus === 'failed' && (
        <div className="rounded-lg border border-red-600 bg-red-950 p-4 text-red-400 font-semibold flex items-center gap-2">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Analysis failed. Please try uploading again.
        </div>
      )}

      {/* Connection error */}
      {error && (
        <div className="rounded-lg border border-yellow-600 bg-yellow-950 p-4 text-yellow-400 text-sm">
          {error}
        </div>
      )}
    </div>
  )
}
