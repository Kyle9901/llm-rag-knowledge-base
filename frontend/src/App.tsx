import { useEffect, useState } from "react";
import { ChatPanel } from "./components/chat/ChatPanel";
import { SessionSidebar } from "./components/chat/SessionSidebar";
import { SettingsModal } from "./components/common/SettingsModal";
import { UploadPanel } from "./components/upload/UploadPanel";
import { useSettingsStore } from "./stores/settings.store";

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [isDesktop, setIsDesktop] = useState<boolean>(window.innerWidth >= 1024);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);
  const themeMode = useSettingsStore((state) => state.themeMode);
  const sidebarCollapsed = useSettingsStore((state) => state.sidebarCollapsed);
  const setSidebarCollapsed = useSettingsStore((state) => state.setSidebarCollapsed);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const root = document.documentElement;
    const applyTheme = () => {
      const useDark = themeMode === "dark" || (themeMode === "system" && media.matches);
      root.classList.toggle("dark", useDark);
    };
    applyTheme();
    media.addEventListener("change", applyTheme);
    return () => {
      media.removeEventListener("change", applyTheme);
    };
  }, [themeMode]);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    const apply = () => {
      setIsDesktop(media.matches);
      if (media.matches) {
        setMobileSidebarOpen(false);
      }
    };
    apply();
    media.addEventListener("change", apply);
    return () => {
      media.removeEventListener("change", apply);
    };
  }, []);

  const showSidebar = isDesktop ? !sidebarCollapsed : mobileSidebarOpen;
  const onToggleSidebar = () => {
    if (isDesktop) {
      setSidebarCollapsed(!sidebarCollapsed);
      return;
    }
    setMobileSidebarOpen((prev) => !prev);
  };

  return (
    <main className="m-1 h-[calc(100vh-8px)] w-[calc(100vw-8px)] overflow-hidden rounded-xl bg-white text-slate-900 dark:bg-black dark:text-white">
      {!showSidebar ? (
        <button
          type="button"
          aria-label="展开侧边栏"
          title="展开侧边栏"
          className="fixed left-2 top-2 z-50 h-9 w-9 rounded-md text-lg leading-none text-slate-700 transition hover:bg-slate-200 dark:text-white dark:hover:bg-white/10"
          onClick={onToggleSidebar}
        >
          ☰
        </button>
      ) : null}
      {!showSidebar ? (
        <button
          type="button"
          aria-label="打开系统设置"
          title="系统设置"
          className="fixed bottom-2 left-2 z-50 h-9 w-9 rounded-full text-base leading-none text-slate-700 transition hover:bg-slate-200 dark:text-white dark:hover:bg-white/10"
          onClick={() => setSettingsOpen(true)}
        >
          ⚙
        </button>
      ) : null}

      <section className="flex h-full w-full">
        {showSidebar ? (
          <aside
            className={`z-40 flex h-full flex-col bg-slate-100/85 dark:bg-[#070707] ${
              isDesktop
                ? "w-[clamp(240px,28vw,360px)]"
                : "fixed inset-y-0 left-0 w-[min(86vw,360px)] shadow-2xl"
            }`}
          >
            <div className="px-3 pb-2 pt-2">
              <button
                type="button"
                aria-label="收起侧边栏"
                title="收起侧边栏"
                className="h-9 w-9 rounded-md text-lg leading-none text-slate-700 transition hover:bg-slate-200 dark:text-white dark:hover:bg-white/10"
                onClick={onToggleSidebar}
              >
                ☰
              </button>
            </div>

            <div className="border-t border-b border-slate-200 p-3 dark:border-white/10">
              <UploadPanel embedded />
            </div>

            <div className="min-h-0 flex-1 p-3">
              <SessionSidebar embedded />
            </div>

            <div className="px-3 pb-3">
              <button
                type="button"
                aria-label="打开系统设置"
                title="系统设置"
                className="h-9 w-9 rounded-full text-base leading-none text-slate-700 transition hover:bg-slate-200 dark:text-white dark:hover:bg-white/10"
                onClick={() => setSettingsOpen(true)}
              >
                ⚙
              </button>
            </div>
          </aside>
        ) : null}

        {!isDesktop && mobileSidebarOpen ? (
          <button
            type="button"
            aria-label="关闭侧边栏遮罩"
            className="fixed inset-0 z-30 bg-black/45"
            onClick={() => setMobileSidebarOpen(false)}
          />
        ) : null}

        <div
          className={`min-w-0 flex-1 ${
            showSidebar && isDesktop ? "border-l border-slate-200 dark:border-white/15" : ""
          }`}
        >
          <ChatPanel />
        </div>
      </section>

      {settingsOpen ? <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} /> : null}
    </main>
  );
}
