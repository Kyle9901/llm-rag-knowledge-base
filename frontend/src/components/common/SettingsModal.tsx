import { FormEvent, useState } from "react";
import { useAuthStore } from "../../stores/auth.store";
import { useSettingsStore } from "../../stores/settings.store";

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
}

export function SettingsModal({ open, onClose }: SettingsModalProps) {
  const token = useAuthStore((state) => state.token);
  const setToken = useAuthStore((state) => state.setToken);
  const logout = useAuthStore((state) => state.logout);
  const themeMode = useSettingsStore((state) => state.themeMode);
  const setThemeMode = useSettingsStore((state) => state.setThemeMode);

  const [tokenInput, setTokenInput] = useState<string>(token ?? "");

  if (!open) {
    return null;
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextToken = tokenInput.trim();
    if (!nextToken) {
      return;
    }
    setToken(nextToken);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 px-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-200 bg-white p-5 shadow-xl dark:border-white/30 dark:bg-black">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">设置</h2>
          <button
            type="button"
            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs hover:bg-slate-100 dark:border-white/30 dark:text-white dark:hover:bg-neutral-900"
            onClick={onClose}
          >
            关闭
          </button>
        </div>

        <form className="space-y-5" onSubmit={onSubmit}>
          <section>
            <p className="mb-2 text-sm font-medium text-slate-700 dark:text-white">API Token</p>
            <input
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="输入后端 API_AUTH_TOKEN"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none dark:border-white/30 dark:bg-black dark:text-white"
            />
            <p className="mt-1 text-xs text-slate-500 dark:text-white/70">用于自动注入 Bearer 鉴权头。</p>
            <div className="mt-2 flex gap-2">
              <button
                type="submit"
                className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-700 dark:bg-white dark:text-black dark:hover:bg-slate-200"
              >
                保存 Token
              </button>
              <button
                type="button"
                className="rounded-md border border-slate-300 px-3 py-2 text-xs hover:bg-slate-100 dark:border-white/30 dark:text-white dark:hover:bg-neutral-900"
                onClick={() => {
                  logout();
                  setTokenInput("");
                }}
              >
                清除 Token
              </button>
            </div>
          </section>

          <section className="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-white/30 dark:bg-black">
            <p className="text-sm font-medium text-slate-700 dark:text-white">主题</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-white/70">支持系统、浅色、深色模式。</p>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {([
                { id: "system", label: "系统" },
                { id: "light", label: "浅色" },
                { id: "dark", label: "深色" },
              ] as const).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setThemeMode(item.id)}
                  className={`rounded-md border px-3 py-2 text-xs transition ${
                    themeMode === item.id
                      ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-white dark:bg-white dark:text-black"
                      : "border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-white/30 dark:text-white dark:hover:bg-neutral-900"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </section>
        </form>
      </div>
    </div>
  );
}
