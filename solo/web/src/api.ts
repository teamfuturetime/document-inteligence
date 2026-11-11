export type Kind = 'invoice' | 'application'
export type Mode = 'rules' | 'vlm' | 'hybrid'
export type OCRProvider = 'tesseract' | 'ocrspace'
export type Values = Record<string, string | number | null>
export interface Field { value: string | number | null; confidence: number | null; confidence_source: string; source: string; evidence: string[]; warnings: string[] }
export interface Extraction { schema_version: string; document_type: Kind; document_sha256: string; mode: Mode; fields: Record<string, Field>; ocr_text: string; provenance: Record<string, unknown>; warnings: string[] }
export interface Validation { valid: boolean; values: Values; errors: Record<string, string> }
export interface Schema { title: string; fields: { key: string; label: string; type: string }[] }
export type Catalog = Record<Kind, Schema>
export interface OCRStatus { ready: boolean; reason?: string | null; provider?: OCRProvider; configured?: boolean }
export interface Health { ocr: OCRStatus; ocr_providers?: Record<OCRProvider, OCRStatus>; vlm: { configured: boolean; provider: string; model: string | null } }

export async function call<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, options)
  const payload = await response.json()
  if (!response.ok) throw new Error(payload?.error?.message ?? `Request thất bại (${response.status}).`)
  return payload as T
}

export function post<T>(path: string, body: unknown, signal: AbortSignal) {
  return call<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal })
}
