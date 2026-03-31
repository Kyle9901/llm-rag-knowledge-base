import { FormEvent, useMemo, useState } from "react";
import { useChatStore } from "../../stores/chat.store";

function formatUpdatedAt(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const now = new Date();
  const isSameDay =
    now.getFullYear() === date.getFullYear() &&
    now.getMonth() === date.getMonth() &&
    now.getDate() === date.getDate();
  if (isSameDay) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday =
    yesterday.getFullYear() === date.getFullYear() &&
    yesterday.getMonth() === date.getMonth() &&
    yesterday.getDate() === date.getDate();
  if (isYesterday) {
    return "昨天";
  }
  return date.toLocaleDateString([], { month: "2-digit", day: "2-digit" });
}

interface SessionSidebarProps {
  embedded?: boolean;
}

export function SessionSidebar({ embedded = false }: SessionSidebarProps) {
  const [keyword, setKeyword] = useState<string>("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState<string>("");
  const { sessionId, sessions, isStreaming, switchSession, startNewSession, deleteSession, updateSessionTitle } =
    useChatStore();

  const sortedSessions = useMemo(
    () =>
      [...sessions].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()),
    [sessions],
  );
  const filteredSessions = useMemo(() => {
    const normalized = keyword.trim().toLowerCase();
    if (!normalized) {
      return sortedSessions;
    }
    return sortedSessions.filter(
      (item) =>
        item.title.toLowerCase().includes(normalized) || item.preview.toLowerCase().includes(normalized),
    );
  }, [keyword, sortedSessions]);

  const onRenameSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!editingId) {
      return;
    }
    updateSessionTitle(editingId, editingTitle);
    setEditingId(null);
    setEditingTitle("");
  };

  return (
    <section
      className={
        embedded
          ? "flex h-full min-h-0 flex-col p-0"
          : "rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-white/30 dark:bg-black"
      }
    >
      <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-white">对话</p>

      <button
        type="button"
        onClick={startNewSession}
        disabled={isStreaming}
        className="mb-3 w-full rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-black dark:hover:bg-slate-200"
      >
        新建对话
      </button>

      <input
        value={keyword}
        onChange={(event) => setKeyword(event.target.value)}
        placeholder="搜索会话标题或内容"
        className="mb-3 w-full rounded-md border border-slate-300 px-2.5 py-1.5 text-xs focus:border-slate-500 focus:outline-none dark:border-white/30 dark:bg-black dark:text-white"
      />

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {filteredSessions.map((item) => {
          const active = item.id === sessionId;
          return (
            <article
              key={item.id}
              className={`group rounded-lg p-2 ${
                active
                  ? "bg-slate-100 dark:bg-white/10"
                  : "bg-transparent hover:bg-slate-50 dark:hover:bg-white/5"
              }`}
            >
              {editingId === item.id ? (
                <form className="space-y-1.5" onSubmit={onRenameSubmit}>
                  <input
                    autoFocus
                    value={editingTitle}
                    onChange={(event) => setEditingTitle(event.target.value)}
                    className="w-full rounded-md border border-slate-300 px-2 py-1 text-xs focus:border-slate-500 focus:outline-none dark:border-white/30 dark:bg-black dark:text-white"
                  />
                  <div className="flex justify-end gap-2 text-[11px]">
                    <button
                      type="button"
                      className="text-slate-500 hover:text-slate-700 dark:text-white/70"
                      onClick={() => {
                        setEditingId(null);
                        setEditingTitle("");
                      }}
                    >
                      取消
                    </button>
                    <button type="submit" className="text-blue-600 hover:text-blue-700">
                      保存
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  type="button"
                  onClick={() => switchSession(item.id)}
                  disabled={isStreaming || active}
                  className="w-full text-left disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <p className="truncate text-sm font-medium text-slate-800 dark:text-white">{item.title}</p>
                  <p className="mt-1 text-[11px] text-slate-500 dark:text-white/60">{formatUpdatedAt(item.updatedAt)}</p>
                </button>
              )}
              {editingId !== item.id ? (
                <div className="mt-1.5 flex justify-end gap-2 opacity-0 transition group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(item.id);
                      setEditingTitle(item.title);
                    }}
                    disabled={isStreaming}
                    aria-label="重命名对话"
                    title="重命名"
                    className="rounded p-1 text-[11px] text-slate-500 hover:bg-blue-50 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-40 dark:text-white/70 dark:hover:bg-white/10 dark:hover:text-white"
                  >
                    ✎
                  </button>
                  {sortedSessions.length > 1 ? (
                    <button
                      type="button"
                      onClick={() => deleteSession(item.id)}
                      disabled={isStreaming}
                      aria-label="删除对话"
                      title="删除"
                      className="rounded p-1 text-[11px] text-slate-500 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40 dark:text-white/70 dark:hover:bg-white/10 dark:hover:text-white"
                    >
                      🗑
                    </button>
                  ) : null}
                </div>
              ) : null}
            </article>
          );
        })}
        {filteredSessions.length === 0 ? (
          <p className="py-3 text-center text-xs text-slate-500 dark:text-white/70">未找到匹配会话</p>
        ) : null}
      </div>
    </section>
  );
}
