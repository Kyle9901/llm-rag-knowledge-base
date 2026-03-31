import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  logout: () => void;
}

const TOKEN_STORAGE_KEY = "rag_api_auth_token";

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      isAuthenticated: false,
      setToken: (token: string): void => {
        set({ token, isAuthenticated: true });
      },
      logout: (): void => {
        set({ token: null, isAuthenticated: false });
      },
    }),
    {
      name: TOKEN_STORAGE_KEY,
      partialize: (state) => ({ token: state.token }),
      onRehydrateStorage: () => (state) => {
        if (!state) {
          return;
        }
        state.isAuthenticated = Boolean(state.token);
      },
    },
  ),
);
