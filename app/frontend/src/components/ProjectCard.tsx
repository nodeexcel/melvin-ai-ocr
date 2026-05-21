import Link from 'next/link'
import type { ProjectOut } from '@/types'

const STATUS_COLORS: Record<string, string> = {
  pending:    'bg-gray-600 text-gray-200',
  processing: 'bg-blue-900 text-blue-200',
  done:       'bg-green-900 text-green-200',
  failed:     'bg-red-900 text-red-200',
}

interface Props {
  project: ProjectOut
  onDelete: (id: string) => void
}

export default function ProjectCard({ project, onDelete }: Props) {
  const href = project.status === 'done'
    ? `/projects/${project.id}/results`
    : `/projects/${project.id}/progress`

  return (
    <div className="bg-brand-gray rounded-lg p-4 flex items-center justify-between hover:border hover:border-brand-yellow transition">
      <Link href={href} className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[project.status] ?? 'bg-gray-600'}`}>
            {project.status.toUpperCase()}
          </span>
          <span className="font-semibold text-white truncate">{project.name}</span>
        </div>
        <p className="text-gray-400 text-sm mt-1 truncate">{project.original_filename}</p>
        <p className="text-gray-500 text-xs mt-0.5">
          {new Date(project.created_at).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
          })}
        </p>
      </Link>
      <button
        onClick={() => onDelete(project.id)}
        className="ml-4 text-gray-500 hover:text-red-400 transition text-sm"
        aria-label="Delete project"
      >
        ✕
      </button>
    </div>
  )
}
