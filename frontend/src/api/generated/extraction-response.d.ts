/* Generated from schemas/v1/extraction-response.schema.json. Do not edit.
 * Source SHA-256: 5725f5ef7d15131923988073eade01b8945f6acabaca6b55c80a2224370979f1
 */

export type ConfigVersion = string;
export type DocumentId = string;
export type Confidence = number | null;
export type X0 = number;
export type X1 = number;
export type Y0 = number;
export type Y1 = number;
export type Page = 1;
export type Text = string;
export type Evidence = Evidence1[];
export type Value = "VND" | null;
export type Warnings = string[];
export type Confidence1 = number | null;
export type Evidence2 = Evidence1[];
export type Value1 = string | null;
export type Warnings1 = string[];
export type Confidence2 = number | null;
export type Evidence3 = Evidence1[];
export type Value2 = string | null;
export type Warnings2 = string[];
export type Confidence3 = number | null;
export type Evidence4 = Evidence1[];
export type Value3 = string | null;
export type Warnings3 = string[];
export type Confidence4 = number | null;
export type Evidence5 = Evidence1[];
export type Value4 = number | null;
export type Warnings4 = string[];
export type Mode = "mock" | "real";
export type OcrVersion = string;
export type PipelineVersion = string;
export type SchemaVersion = "1.0.0";
export type Warnings5 = string[];

export interface ExtractionResponse {
  config_version: ConfigVersion;
  document_id: DocumentId;
  fields: ExtractedFields;
  mode: Mode;
  ocr_version: OcrVersion;
  pipeline_version: PipelineVersion;
  schema_version: SchemaVersion;
  warnings: Warnings5;
}
export interface ExtractedFields {
  currency: ExtractedFieldLiteralVND;
  invoice_date: ExtractedFieldAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueJsonSchemaExtraFormatDateMetadata_PydanticGeneralMetadataPatternD4D2D2$AfterValidator;
  invoice_number: ExtractedFieldAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength100_PydanticGeneralMetadataPatternS;
  seller_name: ExtractedFieldAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength200_PydanticGeneralMetadataPatternS;
  total_amount: ExtractedFieldAnnotatedIntFieldInfoAnnotationNoneTypeRequiredTrueMetadataGeGe0LeLe9007199254740991;
}
export interface ExtractedFieldLiteralVND {
  confidence: Confidence;
  evidence: Evidence;
  value: Value;
  warnings: Warnings;
}
export interface Evidence1 {
  box: BoundingBox;
  page: Page;
  text: Text;
}
export interface BoundingBox {
  x0: X0;
  x1: X1;
  y0: Y0;
  y1: Y1;
}
export interface ExtractedFieldAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueJsonSchemaExtraFormatDateMetadata_PydanticGeneralMetadataPatternD4D2D2$AfterValidator {
  confidence: Confidence1;
  evidence: Evidence2;
  value: Value1;
  warnings: Warnings1;
}
export interface ExtractedFieldAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength100_PydanticGeneralMetadataPatternS {
  confidence: Confidence2;
  evidence: Evidence3;
  value: Value2;
  warnings: Warnings2;
}
export interface ExtractedFieldAnnotatedStrFieldInfoAnnotationNoneTypeRequiredTrueMetadataMinLenMinLength1MaxLenMaxLength200_PydanticGeneralMetadataPatternS {
  confidence: Confidence3;
  evidence: Evidence4;
  value: Value3;
  warnings: Warnings3;
}
export interface ExtractedFieldAnnotatedIntFieldInfoAnnotationNoneTypeRequiredTrueMetadataGeGe0LeLe9007199254740991 {
  confidence: Confidence4;
  evidence: Evidence5;
  value: Value4;
  warnings: Warnings4;
}
