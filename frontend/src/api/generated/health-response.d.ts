/* Generated from schemas/v1/health-response.schema.json. Do not edit.
 * Source SHA-256: 184f1155a4aad0396c71f7104f970fd9d0ebafe5db3181e1f6cdf0d89f6c3a5f
 */

export type Mode = "mock" | "real";
export type OcrReady = boolean;
export type Status = "ok";

export interface HealthResponse {
  mode: Mode;
  ocr_ready: OcrReady;
  status: Status;
}
