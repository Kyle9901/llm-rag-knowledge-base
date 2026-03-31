import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SettingsState {
  streamEnabled: boolean;
  themeMode: "system" | "light" | "dark";
  sidebarCollapsed: boolean;
  setStreamEnabled: (enabled: boolean) => void;
  setThemeMode: (mode: "system" | "light" | "dark") => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      streamEnabled: true,
      themeMode: "system",
      sidebarCollapsed: false,
      setStreamEnabled: (enabled: boolean) => {
        set({ streamEnabled: enabled });
      },
      setThemeMode: (mode: "system" | "light" | "dark") => {
        set({ themeMode: mode });
      },
      setSidebarCollapsed: (collapsed: boolean) => {
        set({ sidebarCollapsed: collapsed });
      },
    }),
    {
      name: "rag_frontend_settings",
      partialize: (state) => ({
        streamEnabled: state.streamEnabled,
        themeMode: state.themeMode,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    },
  ),
);
