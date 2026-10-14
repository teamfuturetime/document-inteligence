/* Generated from schemas/v1/invoice-values.schema.json. Do not edit.
 * Source SHA-256: 24e4a2e927fbbc817db80c66e0f3324002f0f73dd743c400e1b086b7b847e3cc
 */

export type Currency = "VND" | null;
export type InvoiceDate = string | null;
export type InvoiceNumber = string | null;
export type SellerName = string | null;
export type TotalAmount = number | null;

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
