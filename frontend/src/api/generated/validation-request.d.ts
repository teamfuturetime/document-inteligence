/* Generated from schemas/v1/validation-request.schema.json. Do not edit.
 * Source SHA-256: b728025292ae50e446195983d97c293784da559ffb7a9be9c61514d703e1e5f0
 */

export type SchemaVersion = "1.0.0";
export type Currency = string | null;
export type InvoiceDate = string | null;
export type InvoiceNumber = string | null;
export type SellerName = string | null;
export type TotalAmount = string | null;

export interface ValidationRequest {
  schema_version: SchemaVersion;
  values: ReviewedValues;
}
/**
 * Raw browser input; services later normalize these strings.
 */
export interface ReviewedValues {
  currency: Currency;
  invoice_date: InvoiceDate;
  invoice_number: InvoiceNumber;
  seller_name: SellerName;
  total_amount: TotalAmount;
}
