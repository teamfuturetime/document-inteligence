import Ajv2020 from 'ajv/dist/2020.js'
import healthSchema from '../../../schemas/v1/health-response.schema.json'
import errorSchema from '../../../schemas/v1/api-error.schema.json'
import type { HealthResponse } from './generated/health-response'
import type { APIErrorResponse } from './generated/api-error'

const validator = new Ajv2020()
const isHealthResponse = validator.compile<HealthResponse>(healthSchema)
const isAPIError = validator.compile<APIErrorResponse>(errorSchema)

export class RequestError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'RequestError'
  }
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  let response: Response
  try {
    const deadline = AbortSignal.timeout(5000)
    response = await fetch('/health', {
      signal: signal ? AbortSignal.any([signal, deadline]) : deadline,
      headers: { Accept: 'application/json' },
    })
  } catch (error) {
    if (typeof error === 'object' && error !== null && 'name' in error && error.name === 'TimeoutError') {
      throw new RequestError('Backend chưa phản hồi sau 5 giây. Hãy thử lại.')
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
  if (!isHealthResponse(body)) {
    throw new RequestError('Phản hồi backend không đúng contract v1.0.0.', response.status)
  }
  return body
}
