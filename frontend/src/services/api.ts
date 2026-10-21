import axios from "axios";
import type { DocumentRecord, Extraction } from "../types/document";

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1", timeout: 30000 });

export function getApiErrorMessage(error: unknown, fallback: string) {
  if (!axios.isAxiosError(error)) return fallback;
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap(item => typeof item?.msg === "string" ? [item.msg] : []);
    if (messages.length) return messages.join("; ");
  }
  if (error.code === "ECONNABORTED") return "Yêu cầu quá thời gian chờ. Vui lòng thử lại.";
  return fallback;
}

export async function uploadDocument(file: File, onProgress?: (percent: number) => void) {
  const form = new FormData();
  form.append("file", file);
  const response = await api.post<DocumentRecord>("/documents", form, {
    onUploadProgress: (event) => onProgress?.(event.total ? Math.round(event.loaded * 100 / event.total) : 0),
  });
  return response.data;
}

export async function processDocument(id: string) { await api.post(`/documents/${id}/process`); }
export async function getExtraction(id: string) { return (await api.get<Extraction>(`/documents/${id}/extraction`)).data; }
export async function getDocument(id: string) { return (await api.get<DocumentRecord>(`/documents/${id}`)).data; }
export function documentContentUrl(id: string) { return `${api.defaults.baseURL}/documents/${id}/content`; }
export async function updateExtraction(id: string, extraction: Extraction) {
  return (await api.patch<Extraction>(`/documents/${id}/extraction`, { data: extraction.data, warnings: extraction.warnings })).data;
}
export async function confirmExtraction(id: string) { return (await api.post<Extraction>(`/documents/${id}/confirm`)).data; }
export async function listDocuments(query = "", status = "", offset = 0, limit = 20) {
  return (await api.get<{ items: DocumentRecord[]; total: number }>("/documents", {
    params: { q: query || undefined, status: status || undefined, offset, limit },
  })).data;
}
