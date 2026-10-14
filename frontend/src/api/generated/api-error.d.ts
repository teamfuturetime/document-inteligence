/* Generated from schemas/v1/api-error.schema.json. Do not edit.
 * Source SHA-256: 451274f1b500f9f0a37962232a3b022b49d19a661fc53f54dfd527a3998e5900
 */

export type Code =
  | "file_too_large"
  | "unsupported_media_type"
  | "invalid_document"
  | "multiple_pages"
  | "image_too_large"
  | "invalid_request"
  | "ocr_unavailable"
  | "processing_timeout"
  | "internal_error";
export type Field = ("invoice_number" | "invoice_date" | "seller_name" | "total_amount" | "currency") | null;
export type Message = string;

export interface APIErrorResponse {
  error: APIErrorDetail;
}
export interface APIErrorDetail {
  code: Code;
  field: Field;
  message: Message;
}
