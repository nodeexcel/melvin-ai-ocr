export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ProjectOut {
  id: string
  name: string
  original_filename: string
  status: 'pending' | 'processing' | 'done' | 'failed'
  created_at: string
  completed_at: string | null
}

export interface ProjectDetail extends ProjectOut {
  raw_json: Record<string, unknown> | null
  report_pdf_url: string | null
}

export interface ProgressEvent {
  step: string
  message: string
  progress_pct: number
  timestamp?: string
  status?: string
}
