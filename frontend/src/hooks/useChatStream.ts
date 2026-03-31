import { useCallback, useEffect, useRef } from "react";
import { EventStreamContentType, fetchEventSource } from "@microsoft/fetch-event-source";
import { API_BASE_URL } from "../api/client";
import { useAuthStore } from "../stores/auth.store";
import { useChatStore } from "../stores/chat.store";

interface StreamPayload {
  query: string;
  userId?: string;
}

interface StreamTokenEvent {
  token: string;
}

const DEFAULT_API_TOKEN = import.meta.env.VITE_API_AUTH_TOKEN ?? "dev-static-token";

function buildSseDiagnosticMessage(baseUrl: string): string {
  return [
    "流式请求失败（failed to fetch）。",
    "请按以下顺序排查：",
    `1) 后端服务是否可访问：${baseUrl}/api/v1/health`,
    "2) CORS 白名单是否包含前端地址（127.0.0.1:5173）",
    "3) 代理/VPN 是否拦截本地端口或 SSE 长连接",
    "4) 设置中的 API Token 是否正确",
    "5) 后端 .env 中 OPENAI_API_KEY（DeepSeek）是否有效",
  ].join("\n");
}

function parseTokenEvent(rawData: string): StreamTokenEvent | null {
  if (!rawData || rawData === "[DONE]") {
    return null;
  }
  try {
    const parsed = JSON.parse(rawData) as Partial<StreamTokenEvent>;
    if (typeof parsed.token === "string") {
      return { token: parsed.token };
    }
    return null;
  } catch {
    return null;
  }
}

export function useChatStream(debounceMs = 180) {
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<number | null>(null);
  const retryCountRef = useRef<number>(0);

  const token = useAuthStore((state) => state.token);
  const {
    sessionId,
    isStreaming,
    addMessage,
    appendAssistantToken,
    setError,
    setStreaming,
  } = useChatStore();

  const stop = useCallback((): void => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setStreaming(false);
  }, [setStreaming]);

  const start = useCallback(
    (payload: StreamPayload): void => {
      const authToken = token?.trim() || DEFAULT_API_TOKEN;

      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }

      debounceRef.current = window.setTimeout(() => {
        void (async () => {
          setError(null);
          setStreaming(true);

          const userMessageId = crypto.randomUUID();
          const assistantMessageId = crypto.randomUUID();
          addMessage({
            id: userMessageId,
            role: "user",
            content: payload.query,
            createdAt: new Date().toISOString(),
            sources: [],
          });
          addMessage({
            id: assistantMessageId,
            role: "assistant",
            content: "",
            createdAt: new Date().toISOString(),
            sources: [],
          });

          const controller = new AbortController();
          abortRef.current = controller;
          retryCountRef.current = 0;

          try {
            await fetchEventSource(`${API_BASE_URL}/api/v1/chat/stream`, {
              method: "POST",
              signal: controller.signal,
              openWhenHidden: true,
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${authToken}`,
              },
              body: JSON.stringify({
                session_id: sessionId,
                query: payload.query,
                stream: true,
                user_id: payload.userId,
              }),
              async onopen(response) {
                if (!response.ok) {
                  throw new Error(`SSE open failed with status ${response.status}`);
                }
                const contentType = response.headers.get("content-type") ?? "";
                if (!contentType.includes(EventStreamContentType)) {
                  throw new Error("Invalid SSE content type.");
                }
              },
              onmessage(message) {
                if (message.data === "[DONE]") {
                  stop();
                  return;
                }
                const event = parseTokenEvent(message.data);
                if (event) {
                  appendAssistantToken(assistantMessageId, event.token);
                }
              },
              onclose() {
                stop();
              },
              onerror(error) {
                if (controller.signal.aborted) {
                  return;
                }
                retryCountRef.current += 1;
                if (retryCountRef.current <= 3) {
                  return retryCountRef.current * 1000;
                }
                const message = error instanceof Error ? error.message : "SSE stream error";
                setError(`流式连接重试失败：${message}`);
                throw error;
              },
            });
          } catch (error) {
            if (!controller.signal.aborted) {
              const raw = error instanceof Error ? error.message : "SSE request failed";
              const message =
                raw.toLowerCase().includes("fetch") || raw.toLowerCase().includes("network")
                  ? buildSseDiagnosticMessage(API_BASE_URL)
                  : raw;
              setError(message);
            }
          } finally {
            setStreaming(false);
          }
        })();
      }, debounceMs);
    },
    [addMessage, appendAssistantToken, debounceMs, sessionId, setError, setStreaming, stop, token],
  );

  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    start,
    stop,
    isStreaming,
  };
}
