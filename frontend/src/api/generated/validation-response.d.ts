/* Generated from schemas/v1/validation-response.schema.json. Do not edit.
 * Source SHA-256: 00c6db1aa1f294c845174a422dd2ffbbe053b36c43debf2205ff7957714ffc47
 */

export type Code = "required" | "invalid_format" | "invalid_date" | "out_of_range" | "unsupported_currency";
export type Field = "invoice_number" | "invoice_date" | "seller_name" | "total_amount" | "currency";
export type Message = string;
export type Errors = FieldError[];
export type Currency = "VND" | null;
export type InvoiceDate = string | null;
export type InvoiceNumber = string | null;
export type SellerName = string | null;
export type TotalAmount = number | null;
export type SchemaVersion = "1.0.0";
export type Valid = boolean;

export interface ValidationResponse {
  errors: Errors;
  normalized_values: InvoiceValues;
  schema_version: SchemaVersion;
  valid: Valid;
}
export interface FieldError {
  code: Code;
  field: Field;
  message: Message;
}
/**
 * All keys required; null explicitly represents a missing value.
 */
export interface InvoiceValues {
  currency: Currency;
  invoice_date: InvoiceDate;
  invoice_number: InvoiceNumber;
  seller_name: SellerName;
  total_amount: TotalAmount;
}
