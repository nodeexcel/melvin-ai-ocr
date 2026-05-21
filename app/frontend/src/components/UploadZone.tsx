'use client'
import { useCallback, useState } from 'react'

interface Props {
  onFile: (file: File) => void
}

export default function UploadZone({ onFile }: Props) {
  const [dragging, setDragging] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file?.type === 'application/pdf') onFile(file)
  }, [onFile])

  return (
    <div
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition ${
        dragging ? 'border-brand-yellow bg-brand-yellow/10' : 'border-brand-lightgray hover:border-brand-yellow'
      }`}
      onClick={() => document.getElementById('pdf-input')?.click()}
    >
      <input
        id="pdf-input"
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }}
      />
      <p className="text-4xl mb-3">📄</p>
      <p className="text-white font-medium">Drop PDF here or click to browse</p>
      <p className="text-gray-500 text-sm mt-1">Structural or architectural plan set (.pdf)</p>
    </div>
  )
}
