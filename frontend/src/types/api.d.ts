export type ChatRole = "user" | "assistant";
export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface UserEntity {
  id: number;
  user_id: string;
  created_at: string;
}

export interface DocumentEntity {
  id: number;
  user_id: number | null;
  session_id: string;
  filename: string;
  file_path: string;
  status: DocumentStatus;
  task_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  session_id: string;
  query: string;
  stream: boolean;
  user_id?: string;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  session_id: string;
}

export interface ChatHistoryItem {
  id: number;
  session_id: string;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatHistoryItem[];
}

export interface DocumentUploadResponse {
  document_id: number;
  task_id: string;
  status: string;
}

export interface TaskStatusResponse {
  task_id: string;
  state: string;
  progress?: string;
  detail?: string;
}
