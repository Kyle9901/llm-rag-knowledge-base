import { DragEvent, useEffect, useRef, useState } from "react";
import { uploadDocument } from "../../api/document.service";
import { useTaskPolling } from "../../hooks/useTaskPolling";
import { useChatStore } from "../../stores/chat.store";

function toStageStatusLabel(stage: string | null): string {
  if (!stage) {
    return "未开始";
  }
  if (stage === "completed") {
    return "已完成";
  }
  if (stage === "failed") {
    return "失败";
  }
  return "处理中";
}

function toSimpleStatusLabel(stage: string | null, isUploading: boolean): string {
  if (isUploading) {
    return "上传中";
  }
  return toStageStatusLabel(stage);
}

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

interface UploadHistoryItem {
  id: string;
  fileName: string;
  fileSize: number;
  sessionId: string;
  status: string;
  taskId: string | null;
  updatedAt: string;
}

const UPLOAD_HISTORY_KEY = "rag_upload_history";
const MAX_UPLOAD_HISTORY = 8;

interface UploadPanelProps {
  embedded?: boolean;
}

export function UploadPanel({ embedded = false }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragging, setDragging] = useState<boolean>(false);
  const [uploadHistory, setUploadHistory] = useState<UploadHistoryItem[]>([]);
  const [activeUploadId, setActiveUploadId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const sessionId = useChatStore((state) => state.sessionId);
  const { task, error, start } = useTaskPolling();

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(UPLOAD_HISTORY_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as UploadHistoryItem[];
      if (!Array.isArray(parsed)) {
        return;
      }
      setUploadHistory(parsed.slice(0, MAX_UPLOAD_HISTORY));
    } catch {
      // 本地历史损坏时忽略并覆盖，不影响主流程。
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(UPLOAD_HISTORY_KEY, JSON.stringify(uploadHistory.slice(0, MAX_UPLOAD_HISTORY)));
  }, [uploadHistory]);

  useEffect(() => {
    if (!task) {
      return;
    }
    const nextStatus = toStageStatusLabel(task.stage);
    setUploadHistory((prev) =>
      prev.map((item) => {
        const matchedByTaskId = item.taskId && item.taskId === task.taskId;
        const matchedByActiveId = !item.taskId && item.id === activeUploadId;
        if (!matchedByTaskId && !matchedByActiveId) {
          return item;
        }
        return {
          ...item,
          taskId: task.taskId,
          status: nextStatus,
          updatedAt: new Date().toISOString(),
        };
      }),
    );
    if (task.stage === "completed" || task.stage === "failed") {
      setActiveUploadId(null);
    }
  }, [activeUploadId, task]);

  const handlePickFile = (nextFile: File | null) => {
    if (!nextFile) {
      return;
    }
    const lowerName = nextFile.name.toLowerCase();
    if (!lowerName.endsWith(".pdf")) {
      setUploadError("仅支持上传 PDF 文件。");
      return;
    }
    setUploadError(null);
    setFile(nextFile);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    const droppedFile = event.dataTransfer.files?.[0] ?? null;
    handlePickFile(droppedFile);
  };

  const onUpload = async (): Promise<void> => {
    if (!file) {
      return;
    }
    setUploadError(null);
    setIsUploading(true);
    const uploadId = crypto.randomUUID();
    setActiveUploadId(uploadId);
    setUploadHistory((prev) => [
      {
        id: uploadId,
        fileName: file.name,
        fileSize: file.size,
        sessionId,
        status: "上传中",
        taskId: null,
        updatedAt: new Date().toISOString(),
      },
      ...prev,
    ].slice(0, MAX_UPLOAD_HISTORY));
    try {
      const response = await uploadDocument({
        file,
        sessionId,
      });
      start(response.task_id);
      setUploadHistory((prev) =>
        prev.map((item) => {
          if (item.id !== uploadId) {
            return item;
          }
          return {
            ...item,
            taskId: response.task_id,
            status: "处理中",
            updatedAt: new Date().toISOString(),
          };
        }),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "上传失败";
      setUploadError(message);
      setUploadHistory((prev) =>
        prev.map((item) => {
          if (item.id !== uploadId) {
            return item;
          }
          return {
            ...item,
            status: "失败",
            updatedAt: new Date().toISOString(),
          };
        }),
      );
      setActiveUploadId(null);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section
      className={
        embedded
          ? "p-0"
          : "rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/30 dark:bg-black"
      }
    >
      <h2 className="text-sm font-semibold text-slate-700 dark:text-white">文档入库</h2>
      <p className="mt-1 text-xs text-slate-500 dark:text-white/70">支持 PDF 拖拽上传，处理完成后可直接提问。</p>

      <div
        className={`mt-3 rounded-lg border-2 border-dashed p-4 transition ${
          dragging
            ? "border-blue-400 bg-blue-50 dark:bg-blue-900/20"
            : "border-slate-300 bg-slate-50 dark:border-white/30 dark:bg-black"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragging(false);
        }}
        onDrop={onDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={(e) => handlePickFile(e.target.files?.[0] ?? null)}
          className="hidden"
        />
        <p className="text-sm text-slate-700 dark:text-white">将 PDF 拖到这里，或点击按钮选择文件</p>
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs hover:bg-slate-100 dark:border-white/30 dark:bg-black dark:text-white dark:hover:bg-neutral-900"
          >
            选择 PDF
          </button>
          <button
            type="button"
            onClick={() => {
              void onUpload();
            }}
            disabled={!file || isUploading}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-black"
          >
            {isUploading ? "上传中..." : "上传并入库"}
          </button>
        </div>

        {file ? (
          <div className="mt-3 rounded-md border border-slate-200 bg-white p-2 text-xs dark:border-white/30 dark:bg-black">
            <p className="truncate text-slate-700 dark:text-white">{file.name}</p>
            <div className="mt-1 flex items-center justify-between text-slate-500 dark:text-white/70">
              <span>{formatFileSize(file.size)}</span>
              <button
                type="button"
                className="hover:text-red-600"
                onClick={() => {
                  setFile(null);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                  }
                }}
              >
                移除
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {uploadError ? <p className="mt-3 whitespace-pre-line text-xs text-red-600">{uploadError}</p> : null}
      {error ? <p className="mt-3 whitespace-pre-line text-xs text-red-600">{error}</p> : null}

      {(task || isUploading) ? (
        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 dark:border-white/30 dark:bg-black dark:text-white/80">
          <p>
            当前状态：
            <span className="ml-1 font-medium text-slate-900 dark:text-white">
              {toSimpleStatusLabel(task?.stage ?? null, isUploading)}
            </span>
          </p>
        </div>
      ) : null}

      {uploadHistory.length > 0 ? (
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-medium text-slate-600 dark:text-white">最近上传</p>
            <button
              type="button"
              className="text-[11px] text-slate-500 hover:text-slate-700 dark:text-white/70"
              onClick={() => setUploadHistory([])}
            >
              清空记录
            </button>
          </div>
          <div className="space-y-2">
            {uploadHistory.slice(0, 5).map((item) => (
              <article
                key={item.id}
                className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs dark:border-white/30 dark:bg-black"
              >
                <p className="truncate text-slate-700 dark:text-white">{item.fileName}</p>
                <div className="mt-1 flex items-center justify-between text-slate-500 dark:text-white/70">
                  <span>{formatFileSize(item.fileSize)}</span>
                  <span>{item.status}</span>
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
