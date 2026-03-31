import { useCallback, useEffect, useRef, useState } from "react";
import { fetchTaskStatus } from "../api/document.service";
import type { TaskStatusResponse } from "../types/api";

export type IngestionStage = "pending" | "ocr" | "vectorizing" | "completed" | "failed";

export interface TaskViewModel {
  taskId: string;
  rawState: string;
  progress: string;
  detail: string;
  stage: IngestionStage;
}

function normalizeStage(payload: TaskStatusResponse): IngestionStage {
  const state = payload.state.toUpperCase();
  const detail = (payload.detail ?? "").toLowerCase();
  const progressValue = Number((payload.progress ?? "0%").replace("%", ""));

  if (state === "SUCCESS" || detail.includes("完成")) {
    return "completed";
  }
  if (state === "FAILURE" || detail.includes("失败")) {
    return "failed";
  }
  if (detail.includes("ocr") || detail.includes("识别") || detail.includes("解析")) {
    return "ocr";
  }
  if (detail.includes("向量") || progressValue >= 70) {
    return "vectorizing";
  }
  return "pending";
}

export function useTaskPolling(intervalMs = 2000) {
  const timerRef = useRef<number | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [task, setTask] = useState<TaskViewModel | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const pollOnce = useCallback(
    async (taskId: string): Promise<void> => {
      const payload = await fetchTaskStatus(taskId);
      const stage = normalizeStage(payload);
      setTask({
        taskId: payload.task_id,
        rawState: payload.state,
        progress: payload.progress ?? "0%",
        detail: payload.detail ?? "",
        stage,
      });

      if (stage === "completed" || stage === "failed") {
        stop();
      }
    },
    [stop],
  );

  const start = useCallback(
    (taskId: string) => {
      stop();
      setTask(null);
      setError(null);
      setIsPolling(true);

      void pollOnce(taskId).catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Polling failed";
        setError(message);
        stop();
      });

      timerRef.current = window.setInterval(() => {
        void pollOnce(taskId).catch((err: unknown) => {
          const message = err instanceof Error ? err.message : "Polling failed";
          setError(message);
          stop();
        });
      }, intervalMs);
    },
    [intervalMs, pollOnce, stop],
  );

  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    task,
    error,
    isPolling,
    start,
    stop,
  };
}
