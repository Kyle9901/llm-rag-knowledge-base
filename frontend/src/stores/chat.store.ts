import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatRole } from "../types/api";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  sources: string[];
}

export interface ChatSession {
  id: string;
  title: string;
  preview: string;
  updatedAt: string;
  customTitle: boolean;
}

interface ChatState {
  sessionId: string;
  messages: ChatMessage[];
  sessions: ChatSession[];
  isStreaming: boolean;
  error: string | null;
  setSessionId: (sessionId: string) => void;
  switchSession: (sessionId: string) => void;
  startNewSession: () => void;
  deleteSession: (sessionId: string) => void;
  updateSessionTitle: (sessionId: string, title: string) => void;
  refreshActiveSessionSummary: (messages: ChatMessage[]) => void;
  setStreaming: (value: boolean) => void;
  setError: (message: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  clearMessages: () => void;
  addMessage: (message: ChatMessage) => void;
  appendAssistantToken: (assistantMessageId: string, token: string) => void;
  updateMessageSources: (messageId: string, sources: string[]) => void;
}

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength)}...`;
}

function normalizeText(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function summarizeTitle(messages: ChatMessage[]): string {
  const firstUser = messages.find((item) => item.role === "user" && normalizeText(item.content));
  if (!firstUser) {
    return "新对话";
  }
  const normalized = normalizeText(firstUser.content);
  const firstSentence = normalized.split(/[\n。！？!?]/).find((part) => part.trim().length > 0)?.trim() ?? normalized;
  return truncate(firstSentence, 24);
}

function summarizePreview(messages: ChatMessage[]): string {
  if (messages.length === 0) {
    return "";
  }
  const last = messages[messages.length - 1];
  return truncate(normalizeText(last.content), 36);
}

function createSession(id: string): ChatSession {
  return {
    id,
    title: "新对话",
    preview: "",
    updatedAt: new Date().toISOString(),
    customTitle: false,
  };
}

function upsertSession(sessions: ChatSession[], next: ChatSession): ChatSession[] {
  return [next, ...sessions.filter((item) => item.id !== next.id)].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );
}

const initialSessionId = crypto.randomUUID();

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessionId: initialSessionId,
      messages: [],
      sessions: [createSession(initialSessionId)],
      isStreaming: false,
      error: null,
      setSessionId: (sessionId: string): void => {
        set((state) => ({
          sessionId,
          messages: [],
          error: null,
          sessions: upsertSession(
            state.sessions,
            state.sessions.find((item) => item.id === sessionId) ?? createSession(sessionId),
          ),
        }));
      },
      switchSession: (sessionId: string): void => {
        get().setSessionId(sessionId);
      },
      startNewSession: (): void => {
        const nextSessionId = crypto.randomUUID();
        set({
          sessionId: nextSessionId,
          messages: [],
          error: null,
          isStreaming: false,
          sessions: upsertSession(get().sessions, createSession(nextSessionId)),
        });
      },
      deleteSession: (sessionId: string): void => {
        set((state) => {
          const nextSessions = state.sessions.filter((item) => item.id !== sessionId);
          if (nextSessions.length === 0) {
            const nextId = crypto.randomUUID();
            return {
              sessions: [createSession(nextId)],
              sessionId: nextId,
              messages: [],
              error: null,
              isStreaming: false,
            };
          }
          if (state.sessionId !== sessionId) {
            return { sessions: nextSessions };
          }
          return {
            sessions: nextSessions,
            sessionId: nextSessions[0].id,
            messages: [],
            error: null,
            isStreaming: false,
          };
        });
      },
      updateSessionTitle: (sessionId: string, title: string): void => {
        const normalized = truncate(normalizeText(title), 20);
        if (!normalized) {
          return;
        }
        set((state) => {
          const current = state.sessions.find((item) => item.id === sessionId) ?? createSession(sessionId);
          return {
            sessions: upsertSession(state.sessions, {
              ...current,
              title: normalized,
              customTitle: true,
              updatedAt: new Date().toISOString(),
            }),
          };
        });
      },
      refreshActiveSessionSummary: (messages: ChatMessage[]): void => {
        set((state) => {
          const current = state.sessions.find((item) => item.id === state.sessionId);
          const nextSession: ChatSession = {
            id: state.sessionId,
            title: current?.customTitle ? current.title : summarizeTitle(messages),
            preview: summarizePreview(messages),
            updatedAt: messages[messages.length - 1]?.createdAt ?? new Date().toISOString(),
            customTitle: current?.customTitle ?? false,
          };
          return { sessions: upsertSession(state.sessions, nextSession) };
        });
      },
      setStreaming: (value: boolean): void => {
        set({ isStreaming: value });
      },
      setError: (message: string | null): void => {
        set({ error: message });
      },
      setMessages: (messages: ChatMessage[]): void => {
        set((state) => {
          const current = state.sessions.find((item) => item.id === state.sessionId);
          const nextSession: ChatSession = {
            id: state.sessionId,
            title: current?.customTitle ? current.title : summarizeTitle(messages),
            preview: summarizePreview(messages),
            updatedAt: messages[messages.length - 1]?.createdAt ?? new Date().toISOString(),
            customTitle: current?.customTitle ?? false,
          };
          return { messages, sessions: upsertSession(state.sessions, nextSession) };
        });
      },
      clearMessages: (): void => {
        set((state) => ({
          messages: [],
          error: null,
          sessions: upsertSession(state.sessions, {
            id: state.sessionId,
            title: state.sessions.find((item) => item.id === state.sessionId)?.title ?? "新对话",
            preview: "",
            updatedAt: new Date().toISOString(),
            customTitle: state.sessions.find((item) => item.id === state.sessionId)?.customTitle ?? false,
          }),
        }));
      },
      addMessage: (message: ChatMessage): void => {
        set((state) => ({ messages: [...state.messages, message] }));
      },
      appendAssistantToken: (assistantMessageId: string, token: string): void => {
        set((state) => ({
          messages: state.messages.map((message) => {
            if (message.id !== assistantMessageId) {
              return message;
            }
            return {
              ...message,
              content: `${message.content}${token}`,
            };
          }),
        }));
      },
      updateMessageSources: (messageId: string, sources: string[]): void => {
        set((state) => ({
          messages: state.messages.map((message) => {
            if (message.id !== messageId) {
              return message;
            }
            return { ...message, sources };
          }),
        }));
      },
    }),
    {
      name: "rag_frontend_chat_state",
      partialize: (state) => ({
        sessionId: state.sessionId,
        messages: state.messages,
        sessions: state.sessions,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) {
          return;
        }
        if (!state.sessionId) {
          state.sessionId = crypto.randomUUID();
        }
        if (!state.sessions || state.sessions.length === 0) {
          state.sessions = [createSession(state.sessionId)];
          return;
        }
        state.sessions = state.sessions.map((item) => ({
          ...item,
          customTitle: item.customTitle ?? false,
        }));
      },
    },
  ),
);
