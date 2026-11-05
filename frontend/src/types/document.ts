export type DocumentRecord = {
  id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  status: "uploaded" | "processing" | "review" | "confirmed" | "failed";
  document_type: string | null;
  created_at: string;
  expires_at: string;
};

export type Extraction = {
  id: string;
  document_id: string;
  data: { document_type?: string; raw_text?: string; fields?: Record<string, { value: unknown; confidence: number; source_text?: string | null; reviewed?: boolean }> };
  warnings: string[];
  confirmed: boolean;
};
