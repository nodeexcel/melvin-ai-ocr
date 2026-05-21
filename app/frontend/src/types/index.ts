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
  raw_json: AnalysisResult | null
  report_pdf_url: string | null
}

export interface ProgressEvent {
  step: string
  message: string
  progress_pct: number
  timestamp?: string
  status?: string
}

export interface AnalysisResult {
  project: {
    name: string
    address: string
    architect: string
    structural_engineer: string
    total_sqft: number
    sheet_list: { sheet_no: string; title: string }[]
  }
  foundation: {
    footing_types: { type: string; width_in: number; depth_in: number; linear_feet: number }[]
    concrete_cubic_yards: number
    rebar: { size: string; spacing_in: number; linear_feet: number; qty_pieces: number }[]
    hold_downs: { model: string; qty: number }[]
  }
  simpson_hardware: { model: string; qty: number; description?: string }[]
  framing_details: { description: string; hardware: string; lumber_sizes: string[] }[]
  wall_framing: { exterior_walls: Record<string, unknown>; headers: unknown[] }
  floor_framing: { joists: unknown[]; beams: unknown[] }
  roof_framing: { rafters: unknown[] }
  waste_factors: Record<string, unknown>
  notes: string[]
}
