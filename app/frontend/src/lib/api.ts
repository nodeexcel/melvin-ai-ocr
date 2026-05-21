import { getToken } from './auth'
import type { ProjectDetail, ProjectOut, TokenResponse } from '@/types'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8037'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export async function listProjects(): Promise<ProjectOut[]> {
  return request<ProjectOut[]>('/api/projects')
}

export async function getProject(id: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/api/projects/${id}`)
}

export async function uploadProject(name: string, file: File): Promise<ProjectOut> {
  const form = new FormData()
  form.append('name', name)
  form.append('file', file)
  return request<ProjectOut>('/api/projects/upload', { method: 'POST', body: form })
}

export async function deleteProject(id: string): Promise<void> {
  await request<void>(`/api/projects/${id}`, { method: 'DELETE' })
}

export function getReportUrl(id: string): string {
  return `${API}/api/projects/${id}/report`
}
