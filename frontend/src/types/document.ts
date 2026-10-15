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
  data: { fields?: Record<string, { value: unknown; confidence: number }> };
  warnings: string[];
  confirmed: boolean;
};
