import type { DocumentDetail } from '../src/features/documents/api';
import type { Capabilities } from '../src/lib/api';

export const capabilities: Capabilities = {
  features: {},
  max_upload_bytes: 5242880,
  model_benchmark_status: 'not_measured',
  ocr_ready: true,
  provider_mode: 'tesseract',
  supported_schemas: [],
};
export function errorDocument(): DocumentDetail {
  return {
    document_id: 'synthetic-error',
    document_type: 'hoa_don',
    filename: 'synthetic.png',
    data_origin: 'synthetic',
    input_sha256: 'a'.repeat(64),
    image_width: 100,
    image_height: 100,
    created_at: '2026-11-19T00:00:00Z',
    latest_run_id: 'old',
    status: 'failed',
    image_url: '/image',
    is_latest_run: true,
    definitions: [
      { field_id: 'seller_name', label: 'Đơn vị bán hàng', value_type: 'text', required: true },
    ],
    run: {
      run_id: 'old',
      status: 'failed',
      created_at: '2026-11-19T00:00:00Z',
      error_code: 'PROCESSING_TIMEOUT',
      fields: [],
      spans: [],
    },
    review: null,
  };
}
export function processedDocument(): DocumentDetail {
  const document = errorDocument();
  return {
    ...document,
    status: 'succeeded',
    latest_run_id: 'new',
    run: { ...document.run, run_id: 'new', status: 'succeeded', error_code: null },
    review: {
      revision: 1,
      review_status: 'draft',
      saved_at: document.created_at,
      fields: { seller_name: { is_reviewed: true, reviewed_value: null } },
      effective_data: { seller_name: null },
      validation_issues: [],
    },
  };
}
