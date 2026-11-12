import type { components } from './api.generated';

export type Capabilities = components['schemas']['Capabilities'];
export type FixtureView = components['schemas']['FixtureView'];
export type FixtureCatalog = components['schemas']['FixtureCatalog'];
export type FieldId = components['schemas']['FieldPrediction']['field_id'];

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { signal });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.error?.message ?? `Không tải được dữ liệu (HTTP ${response.status}).`);
  }
  return response.json() as Promise<T>;
}
