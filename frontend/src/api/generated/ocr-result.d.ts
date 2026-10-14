/* Generated from schemas/v1/ocr-result.schema.json. Do not edit.
 * Source SHA-256: c062ac3968ce74c2cb2dee310912eaa41c3328217e20569da42fea8e3d4fc29f
 */

export type Language = "vie+eng";
export type Mode = "mock" | "real";
export type OcrVersion = string;
export type Height = number;
export type Page = 1;
/**
 * @minItems 9
 * @maxItems 9
 */
export type ToOriginal = [number, number, number, number, number, number, number, number, number];
export type X0 = number;
export type X1 = number;
export type Y0 = number;
export type Y1 = number;
export type Confidence = number | null;
export type Text = string;
export type Tokens = OCRToken[];
export type Width = number;
export type SchemaVersion = "1.0.0";

export interface OCRResult {
  language: Language;
  mode: Mode;
  ocr_version: OcrVersion;
  page: OCRPage;
  schema_version: SchemaVersion;
}
export interface OCRPage {
  height: Height;
  page: Page;
  to_original: ToOriginal;
  tokens: Tokens;
  width: Width;
}
export interface OCRToken {
  box: BoundingBox;
  confidence: Confidence;
  text: Text;
}
export interface BoundingBox {
  x0: X0;
  x1: X1;
  y0: Y0;
  y1: Y1;
}
