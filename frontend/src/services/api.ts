import axios from "axios";
import type { DocumentRecord, Extraction } from "../types/document";

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1", timeout: 30000 });

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
