'use client'
import { getToken } from '@/lib/auth'
import type { AnalysisResult } from '@/types'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8037'

interface ResultsPanelProps {
  projectId: string
  projectName: string
  rawJson: AnalysisResult | null
  reportPdfUrl: string | null
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="text-brand-yellow font-semibold text-sm uppercase tracking-wider mb-3">
      {title}
    </h3>
  )
}

function KeyValueRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start py-1.5 border-b border-brand-lightgray last:border-0">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className="text-white text-sm text-right ml-4">{value}</span>
    </div>
  )
}

function CollapsibleList({ items, label }: { items: unknown[]; label: string }) {
  if (items.length === 0) return <span className="text-gray-500 text-sm">None</span>
  return (
    <details className="mt-1">
      <summary className="text-brand-yellow text-sm cursor-pointer hover:text-yellow-300 select-none">
        {items.length} {label}
      </summary>
      <ul className="mt-2 space-y-1 pl-3">
        {items.map((item, i) => (
          <li key={i} className="text-gray-300 text-xs bg-brand-black rounded px-2 py-1">
            {typeof item === 'object' && item !== null
              ? Object.entries(item as Record<string, unknown>)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' · ')
              : String(item)}
          </li>
        ))}
      </ul>
    </details>
  )
}

export default function ResultsPanel({
  projectId,
  projectName,
  rawJson,
  reportPdfUrl,
}: ResultsPanelProps) {
  const token = getToken()

  function handleDownload() {
    if (!reportPdfUrl) return
    const url = `${API}${reportPdfUrl}${token ? `?token=${token}` : ''}`
    window.open(url, '_blank', 'noopener,noreferrer')
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
            onClick={handleDownload}
            className="bg-brand-yellow text-brand-black font-semibold px-5 py-2.5 rounded-lg hover:bg-yellow-400 transition text-sm shrink-0"
          >
            Download PDF Report
          </button>
        )}
      </div>

      {!rawJson ? (
        <div className="bg-brand-gray rounded-lg p-6 text-center text-gray-400">
          No results available.
        </div>
      ) : (
        <div className="space-y-4">
          {/* Project Info */}
          {rawJson.project && (
            <section className="bg-brand-gray rounded-lg p-5">
              <SectionHeader title="Project Info" />
              {rawJson.project.name && (
                <KeyValueRow label="Project Name" value={rawJson.project.name} />
              )}
              {rawJson.project.address && (
                <KeyValueRow label="Address" value={rawJson.project.address} />
              )}
              {rawJson.project.architect && (
                <KeyValueRow label="Architect" value={rawJson.project.architect} />
              )}
              {rawJson.project.structural_engineer && (
                <KeyValueRow label="Structural Engineer" value={rawJson.project.structural_engineer} />
              )}
              {rawJson.project.total_sqft > 0 && (
                <KeyValueRow
                  label="Total Area"
                  value={`${rawJson.project.total_sqft.toLocaleString()} sq ft`}
                />
              )}
              {rawJson.project.sheet_list?.length > 0 && (
                <div className="mt-2">
                  <CollapsibleList
                    items={rawJson.project.sheet_list}
                    label={`sheet${rawJson.project.sheet_list.length !== 1 ? 's' : ''}`}
                  />
                </div>
              )}
            </section>
          )}

          {/* Foundation */}
          {rawJson.foundation && (
            <section className="bg-brand-gray rounded-lg p-5">
              <SectionHeader title="Foundation" />
              {rawJson.foundation.concrete_cubic_yards > 0 && (
                <KeyValueRow
                  label="Concrete"
                  value={`${rawJson.foundation.concrete_cubic_yards} CY`}
                />
              )}
              {rawJson.foundation.footing_types?.length > 0 && (
                <div className="py-1.5 border-b border-brand-lightgray">
                  <span className="text-gray-400 text-sm">Footing Types</span>
                  <div className="mt-1">
                    <CollapsibleList items={rawJson.foundation.footing_types} label="types" />
                  </div>
                </div>
              )}
              {rawJson.foundation.rebar?.length > 0 && (
                <div className="py-1.5 border-b border-brand-lightgray">
                  <span className="text-gray-400 text-sm">Rebar</span>
                  <div className="mt-1">
                    <CollapsibleList items={rawJson.foundation.rebar} label="entries" />
                  </div>
                </div>
              )}
              {rawJson.foundation.hold_downs?.length > 0 && (
                <div className="py-1.5">
                  <span className="text-gray-400 text-sm">Hold-Downs</span>
                  <div className="mt-1">
                    <CollapsibleList items={rawJson.foundation.hold_downs} label="hold-downs" />
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Simpson Hardware */}
          {rawJson.simpson_hardware && rawJson.simpson_hardware.length > 0 && (
            <section className="bg-brand-gray rounded-lg p-5">
              <SectionHeader title="Simpson Hardware" />
              <div className="space-y-1">
                {rawJson.simpson_hardware.map((hw, i) => (
                  <div
                    key={i}
                    className="flex justify-between items-center py-1.5 border-b border-brand-lightgray last:border-0"
                  >
                    <div>
                      <span className="text-white text-sm font-medium">{hw.model}</span>
                      {hw.description && (
                        <span className="text-gray-500 text-xs ml-2">{hw.description}</span>
                      )}
                    </div>
                    <span className="text-brand-yellow text-sm font-semibold ml-4">
                      × {hw.qty}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Framing */}
          {(rawJson.floor_framing || rawJson.wall_framing || rawJson.roof_framing) && (
            <section className="bg-brand-gray rounded-lg p-5">
              <SectionHeader title="Framing" />
              {rawJson.floor_framing && (
                <>
                  {rawJson.floor_framing.joists?.length > 0 && (
                    <div className="py-1.5 border-b border-brand-lightgray">
                      <span className="text-gray-400 text-sm">Floor Joists</span>
                      <div className="mt-1">
                        <CollapsibleList items={rawJson.floor_framing.joists as unknown[]} label="joists" />
                      </div>
                    </div>
                  )}
                  {rawJson.floor_framing.beams?.length > 0 && (
                    <div className="py-1.5 border-b border-brand-lightgray">
                      <span className="text-gray-400 text-sm">Floor Beams</span>
                      <div className="mt-1">
                        <CollapsibleList items={rawJson.floor_framing.beams as unknown[]} label="beams" />
                      </div>
                    </div>
                  )}
                </>
              )}
              {rawJson.wall_framing && (
                <>
                  {rawJson.wall_framing.headers?.length > 0 && (
                    <div className="py-1.5 border-b border-brand-lightgray">
                      <span className="text-gray-400 text-sm">Wall Headers</span>
                      <div className="mt-1">
                        <CollapsibleList items={rawJson.wall_framing.headers as unknown[]} label="headers" />
                      </div>
                    </div>
                  )}
                </>
              )}
              {rawJson.roof_framing && (
                <>
                  {rawJson.roof_framing.rafters?.length > 0 && (
                    <div className="py-1.5">
                      <span className="text-gray-400 text-sm">Roof Rafters</span>
                      <div className="mt-1">
                        <CollapsibleList items={rawJson.roof_framing.rafters as unknown[]} label="rafters" />
                      </div>
                    </div>
                  )}
                </>
              )}
            </section>
          )}

          {/* Framing Details */}
          {rawJson.framing_details && rawJson.framing_details.length > 0 && (
            <section className="bg-brand-gray rounded-lg p-5">
              <SectionHeader title="Framing Details" />
              <CollapsibleList items={rawJson.framing_details} label="details" />
            </section>
          )}

          {/* Notes */}
          {rawJson.notes && rawJson.notes.length > 0 && (
            <section className="bg-brand-gray rounded-lg p-5">
              <SectionHeader title="Notes" />
              <ul className="space-y-2">
                {rawJson.notes.map((note, i) => (
                  <li key={i} className="text-gray-300 text-sm flex gap-2">
                    <span className="text-brand-yellow mt-0.5">•</span>
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
