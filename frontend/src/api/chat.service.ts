import { http } from "./client";
import type { ChatHistoryResponse, ChatRequest, ChatResponse } from "../types/api";

export async function sendChat(payload: ChatRequest): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>("/api/v1/chat", payload);
  return data;
}

export async function fetchChatHistory(sessionId: string, limit = 50): Promise<ChatHistoryResponse> {
  const { data } = await http.get<ChatHistoryResponse>(`/api/v1/chat/history/${sessionId}`, {
    params: { limit },
  });
  return data;
}
