/* Generated from schemas/v1/final-invoice-values.schema.json. Do not edit.
 * Source SHA-256: da22ebdb460d2ae11223f4865303acc8d311861319f731259a76ec0354370116
 */

export type Currency = "VND";
export type InvoiceDate = string;
export type InvoiceNumber = string;
export type SellerName = string;
export type TotalAmount = number;

export interface FinalInvoiceValues {
  currency: Currency;
  invoice_date: InvoiceDate;
  invoice_number: InvoiceNumber;
  seller_name: SellerName;
  total_amount: TotalAmount;
}
