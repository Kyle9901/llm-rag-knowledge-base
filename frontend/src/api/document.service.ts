import { http } from "./client";
import type { DocumentUploadResponse, TaskStatusResponse } from "../types/api";

export interface UploadDocumentPayload {
  file: File;
  sessionId: string;
  userId?: string;
}

export async function uploadDocument(payload: UploadDocumentPayload): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("session_id", payload.sessionId);
  formData.append("file", payload.file);
  if (payload.userId) {
    formData.append("user_id", payload.userId);
  }

  const { data } = await http.post<DocumentUploadResponse>("/api/v1/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const { data } = await http.get<TaskStatusResponse>(`/api/v1/tasks/${taskId}`);
  return data;
}
