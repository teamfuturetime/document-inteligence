import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import healthSchema from '../../../schemas/v1/health-response.schema.json'
import errorSchema from '../../../schemas/v1/api-error.schema.json'
import extractionSchema from '../../../schemas/v1/extraction-response.schema.json'
import validationSchema from '../../../schemas/v1/validation-response.schema.json'
import exportSchema from '../../../schemas/v1/reviewed-export.schema.json'
import type { HealthResponse } from './generated/health-response'
import type { APIErrorResponse } from './generated/api-error'
import type { ExtractionResponse } from './generated/extraction-response'
import type { ValidationResponse } from './generated/validation-response'
import type { ReviewedValues } from './generated/validation-request'
import type { ReviewedExport } from './generated/reviewed-export'

const validator = new Ajv2020()
addFormats(validator)
const isHealthResponse = validator.compile<HealthResponse>(healthSchema)
const isAPIError = validator.compile<APIErrorResponse>(errorSchema)
const isExtractionResponse = validator.compile<ExtractionResponse>(extractionSchema)
const isValidationResponse = validator.compile<ValidationResponse>(validationSchema)
const isReviewedExport = validator.compile<ReviewedExport>(exportSchema)

export const fieldLabels = {
  invoice_number: 'Số hóa đơn', invoice_date: 'Ngày hóa đơn', seller_name: 'Bên bán',
  total_amount: 'Tổng tiền', currency: 'Tiền tệ',
} as const
export type InvoiceField = keyof typeof fieldLabels
export const invoiceFields = Object.keys(fieldLabels) as InvoiceField[]

export class RequestError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'RequestError'
  }
}

async function requestJSON<T>(
  path: string,
  options: RequestInit,
  isResponse: (body: unknown) => body is T,
  timeout: number,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response
  try {
    const deadline = AbortSignal.timeout(timeout)
    response = await fetch(path, {
      ...options,
      signal: signal ? AbortSignal.any([signal, deadline]) : deadline,
      headers: { Accept: 'application/json', ...options.headers },
    })
  } catch (error) {
    if (typeof error === 'object' && error !== null && 'name' in error && error.name === 'TimeoutError') {
      throw new RequestError(`Backend chưa phản hồi sau ${timeout / 1000} giây. Hãy thử lại.`)
    }
    throw new RequestError('Không kết nối được backend. Kiểm tra server rồi thử lại.')
  }

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new RequestError('Backend trả dữ liệu không phải JSON.', response.status)
  }
  if (!response.ok) {
    throw new RequestError(
      isAPIError(body) ? body.error.message : `Backend trả lỗi HTTP ${response.status}.`,
      response.status,
    )
  }
  if (!isResponse(body)) {
    throw new RequestError('Phản hồi backend không đúng contract v1.0.0.', response.status)
  }
  return body
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return requestJSON('/health', {}, isHealthResponse, 5000, signal)
}

export function uploadDocument(file: File, signal?: AbortSignal): Promise<ExtractionResponse> {
  const body = new FormData()
  body.append('file', file)
  // Browser supplies multipart boundary; setting Content-Type here would break it.
  return requestJSON('/api/v1/extract', { method: 'POST', body }, isExtractionResponse, 65000, signal)
}

export async function validateReviewedValues(values: ReviewedValues, signal?: AbortSignal): Promise<ValidationResponse> {
  const result = await requestJSON('/api/v1/validate', {
    method: 'POST', body: JSON.stringify({ schema_version: '1.0.0', values }),
    headers: { 'Content-Type': 'application/json' },
  }, isValidationResponse, 10000, signal)
  const missing = invoiceFields.filter(field => result.normalized_values[field] === null)
  const invalid = new Set(result.errors.map(error => error.field))
  if (result.valid ? result.errors.length > 0 || missing.length > 0
    : !missing.length || missing.some(field => !invalid.has(field)) || [...invalid].some(field => !missing.includes(field))) {
    throw new RequestError('Phản hồi validation không nhất quán.')
  }
  return result
}

export function reviewedExport(original: ExtractionResponse, validation: ValidationResponse): ReviewedExport {
  if (!validation.valid || validation.errors.length) throw new RequestError('Cần validation hợp lệ trước khi xuất.')
  const output = {
    schema_version: '1.0.0', original_extraction: original, values: validation.normalized_values,
    edited_fields: invoiceFields.filter(field => validation.normalized_values[field] !== original.fields[field].value),
  }
  if (!isReviewedExport(output)) throw new RequestError('Dữ liệu xuất không đúng contract.')
  return output
}
