import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "../stores/auth.store";

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_API_TOKEN = import.meta.env.VITE_API_AUTH_TOKEN ?? "dev-static-token";

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL;

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
});

function buildNetworkDiagnosticMessage(): string {
  return [
    "网络请求失败（failed to fetch）。",
    "请按以下顺序排查：",
    `1) 后端连通性：浏览器访问 ${API_BASE_URL}/api/v1/health`,
    "2) CORS 配置：后端 ALLOWED_ORIGINS 包含当前前端地址（如 http://127.0.0.1:5173）",
    "3) 网络代理：检查 VPN/代理是否拦截 127.0.0.1 或 8000 端口",
    "4) 鉴权与密钥：确认 API Token、OPENAI_API_KEY（DeepSeek）在后端 .env 中有效",
    "5) 协议一致性：避免 https 页面调用 http 接口",
  ].join("\n");
}

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token: string | null = useAuthStore.getState().token;
  const authToken = token?.trim() || DEFAULT_API_TOKEN;
  config.headers.Authorization = `Bearer ${authToken}`;
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (!error.response) {
      return Promise.reject(new Error(buildNetworkDiagnosticMessage()));
    }

    if (error.response?.status === 401) {
      return Promise.reject(new Error("鉴权失败（401）。请检查后端 API_AUTH_TOKEN 或前端 VITE_API_AUTH_TOKEN 配置。"));
    }

    if (error.response?.status === 503) {
      return Promise.reject(
        new Error("服务暂不可用（503）。请检查后端依赖（Redis/PostgreSQL/Celery）是否正常运行。"),
      );
    }

    const message = `请求失败（${error.response.status}）。`;
    return Promise.reject(new Error(message));
  },
);
