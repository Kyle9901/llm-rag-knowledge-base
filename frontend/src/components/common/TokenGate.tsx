import { FormEvent, useState } from "react";
import { useAuthStore } from "../../stores/auth.store";

export function TokenGate() {
  const { token, isAuthenticated, setToken, logout } = useAuthStore();
  const [input, setInput] = useState<string>(token ?? "");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextToken = input.trim();
    if (!nextToken) {
      return;
    }
    setToken(nextToken);
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-700">API Token</h2>
      <p className="mt-1 text-xs text-slate-500">
        填写后端配置的 `API_AUTH_TOKEN`，用于自动注入 Bearer 认证。
      </p>
      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          type="password"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入 API_AUTH_TOKEN"
        />
        <button
          className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700"
          type="submit"
        >
          保存
        </button>
        <button
          className="rounded-md border border-slate-300 px-3 py-2 text-sm hover:bg-slate-100"
          type="button"
          onClick={logout}
        >
          清除
        </button>
      </form>
      <p className="mt-2 text-xs text-slate-500">当前状态：{isAuthenticated ? "已认证" : "未认证"}</p>
    </section>
  );
}
