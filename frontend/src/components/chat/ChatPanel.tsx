import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { fetchChatHistory, sendChat } from "../../api/chat.service";
import type { ChatHistoryItem } from "../../types/api";
import { useChatStream } from "../../hooks/useChatStream";
import type { ChatMessage } from "../../stores/chat.store";
import { useChatStore } from "../../stores/chat.store";
import { useSettingsStore } from "../../stores/settings.store";
import { MarkdownRenderer } from "./MarkdownRenderer";

export function ChatPanel() {
  const [query, setQuery] = useState<string>("");
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const messageListRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const { start, stop, isStreaming } = useChatStream();
  const streamEnabled = useSettingsStore((state) => state.streamEnabled);
  const setStreamEnabled = useSettingsStore((state) => state.setStreamEnabled);
  const {
    messages,
    error,
    sessionId,
    setError,
    setMessages,
    refreshActiveSessionSummary,
    addMessage,
  } = useChatStore();

  const canSubmit = useMemo(
    () => query.trim().length > 0 && !(isStreaming || loadingHistory),
    [query, isStreaming, loadingHistory],
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoadingHistory(true);
      try {
        const history = await fetchChatHistory(sessionId, 50);
        if (cancelled) {
          return;
        }
        const mapped: ChatMessage[] = history.messages.map((item: ChatHistoryItem) => ({
          id: String(item.id),
          role: item.role,
          content: item.content,
          createdAt: item.created_at,
          sources: [],
        }));
        setMessages(mapped);
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "历史记录加载失败";
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoadingHistory(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, setError, setMessages]);

  useEffect(() => {
    const container = messageListRef.current;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  }, [messages, isStreaming]);

  useEffect(() => {
    refreshActiveSessionSummary(messages);
  }, [messages, refreshActiveSessionSummary, sessionId]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    const payloadQuery = query.trim();
    setQuery("");
    setError(null);

    if (streamEnabled) {
      start({ query: payloadQuery });
      return;
    }

    const userMessageId = crypto.randomUUID();
    addMessage({
      id: userMessageId,
      role: "user",
      content: payloadQuery,
      createdAt: new Date().toISOString(),
      sources: [],
    });

    try {
      const response = await sendChat({
        session_id: sessionId,
        query: payloadQuery,
        stream: false,
      });
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        createdAt: new Date().toISOString(),
        sources: response.sources,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "同步对话失败";
      setError(message);
    }
  };

  const onInputKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      // 复用 form 提交流程，保持同步/流式两条路径一致。
      event.currentTarget.form?.requestSubmit();
    }
  };

  const onInputChange = (value: string, element: HTMLTextAreaElement | null) => {
    setQuery(value);
    if (!element) {
      return;
    }
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 180)}px`;
  };

  const hasConversation = messages.length > 0 || isStreaming;

  return (
    <section className="relative flex h-full min-h-0 flex-col">
      <div
        className={`pointer-events-none absolute z-10 origin-left select-none font-semibold text-slate-900 transition-all duration-300 dark:text-white ${
          hasConversation
            ? "left-1 top-1 text-sm"
            : "left-1/2 top-[38%] -translate-x-1/2 -translate-y-1/2 text-3xl"
        }`}
      >
        智能体助手
      </div>

      <div ref={messageListRef} className="flex-1 overflow-y-auto px-3 pb-4 pt-10">
        <div className="mx-auto w-full max-w-[800px] space-y-4">
        {loadingHistory ? <p className="text-sm text-slate-500 dark:text-slate-400">历史消息加载中...</p> : null}
        {messages.map((message) => (
          <article key={message.id}>
            {message.role === "user" ? (
              <div className="flex justify-end">
                <div className="relative w-fit max-w-[66%]">
                  <div className="rounded-[24px] bg-slate-200 px-4 py-2.5 text-sm font-normal leading-[1.65] text-slate-800 dark:bg-white/14 dark:text-white">
                    <p className="whitespace-pre-wrap break-words">{message.content || (isStreaming ? "..." : "")}</p>
                  </div>
                  <span className="absolute -bottom-0.5 -right-1.5 h-3 w-3 rounded-full bg-slate-200 dark:bg-white/14" />
                </div>
              </div>
            ) : (
              <div className="flex w-full items-start gap-3">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-slate-300 text-xs font-semibold text-slate-700 dark:border-white/35 dark:text-white">
                  A
                </div>
                <div className="min-w-0 flex-1 text-[15px] font-normal leading-[1.68] text-slate-800 dark:text-white">
                  {isStreaming && !message.content.trim() ? (
                    <p className="animate-pulse text-sm text-slate-500 dark:text-slate-400">思考中...</p>
                  ) : (
                    <MarkdownRenderer content={message.content} />
                  )}
                  {message.sources.length > 0 ? (
                    <div className="mt-3">
                      <p className="mb-1 text-xs font-medium text-slate-500 dark:text-white/70">来源</p>
                      <ul className="list-disc space-y-1 pl-4 text-xs text-slate-600 dark:text-white/75">
                        {message.sources.map((source) => (
                          <li key={source}>{source}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </div>
            )}
          </article>
        ))}
        </div>
      </div>

      {error ? <p className="whitespace-pre-line px-4 pb-2 text-xs text-red-600">{error}</p> : null}

      {!hasConversation ? (
        <form onSubmit={onSubmit} className="absolute left-0 right-0 top-[46%] z-20 px-3">
          <div className="mx-auto w-full max-w-[800px] pb-2">
            <div className="group relative">
              <textarea
                ref={inputRef}
                value={query}
                onChange={(e) => onInputChange(e.target.value, e.currentTarget)}
                onKeyDown={onInputKeyDown}
                rows={1}
                className="max-h-[180px] min-h-[50px] w-full resize-none rounded-full border border-slate-300 bg-white pl-24 pr-12 py-3 text-sm leading-6 focus:border-slate-500 focus:outline-none dark:border-white/30 dark:bg-black dark:text-white"
                placeholder="输入你的问题（Enter 发送，Shift+Enter 换行）"
              />
              <button
                type="button"
                onClick={() => setStreamEnabled(!streamEnabled)}
                aria-label={streamEnabled ? "切换为非流式" : "切换为流式"}
                title={streamEnabled ? "流式" : "非流式"}
                className="absolute bottom-[17.5px] left-3 rounded-full border border-transparent bg-transparent px-2.5 py-1 text-xs text-slate-500 transition hover:scale-105 group-hover:border-slate-300 group-hover:bg-slate-100 dark:text-white/80 dark:group-hover:border-white/30 dark:group-hover:bg-white/10"
              >
                {streamEnabled ? "流式" : "非流式"}
              </button>
              {query.trim().length > 0 ? (
                <button
                  type="submit"
                  disabled={!canSubmit}
                  aria-label="发送消息"
                  title="发送"
                  className="absolute bottom-[15px] right-2 h-8 w-8 rounded-full border border-transparent bg-transparent text-sm font-semibold text-slate-700 transition hover:scale-105 group-hover:border-slate-300 group-hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-white dark:group-hover:border-white/30 dark:group-hover:bg-white/10"
                >
                  ↑
                </button>
              ) : null}
            </div>
          </div>
        </form>
      ) : (
      <form onSubmit={onSubmit} className="mt-auto p-3">
        <div className="mx-auto w-full max-w-[800px] pb-2">
          <div className="group relative">
            <textarea
              ref={inputRef}
              value={query}
              onChange={(e) => onInputChange(e.target.value, e.currentTarget)}
              onKeyDown={onInputKeyDown}
              rows={1}
              className="max-h-[180px] min-h-[50px] w-full resize-none rounded-full border border-slate-300 bg-white pl-24 pr-12 py-3 text-sm leading-6 focus:border-slate-500 focus:outline-none dark:border-white/30 dark:bg-black dark:text-white"
              placeholder="输入你的问题（Enter 发送，Shift+Enter 换行）"
            />

            <button
              type="button"
              onClick={() => setStreamEnabled(!streamEnabled)}
              aria-label={streamEnabled ? "切换为非流式" : "切换为流式"}
              title={streamEnabled ? "流式" : "非流式"}
              className="absolute bottom-[17.5px] left-3 rounded-full border border-transparent bg-transparent px-2.5 py-1 text-xs text-slate-500 transition hover:scale-105 group-hover:border-slate-300 group-hover:bg-slate-100 dark:text-white/80 dark:group-hover:border-white/30 dark:group-hover:bg-white/10"
            >
              {streamEnabled ? "流式" : "非流式"}
            </button>

            {query.trim().length > 0 ? (
              <button
                type="submit"
                disabled={!canSubmit}
                aria-label="发送消息"
                title="发送"
                className="absolute bottom-[15px] right-2 h-8 w-8 rounded-full border border-transparent bg-transparent text-sm font-semibold text-slate-700 transition hover:scale-105 group-hover:border-slate-300 group-hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-white dark:group-hover:border-white/30 dark:group-hover:bg-white/10"
              >
                ↑
              </button>
            ) : null}
          </div>

          {isStreaming ? (
            <div className="mt-1.5 flex justify-end">
              <button
                type="button"
                onClick={stop}
                className="rounded-full border border-slate-300 px-3 py-1 text-xs hover:bg-slate-100 dark:border-white/30 dark:text-white dark:hover:bg-neutral-900"
              >
                停止
              </button>
            </div>
          ) : null}
        </div>
      </form>
      )}
    </section>
  );
}
