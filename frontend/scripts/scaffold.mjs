import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();

const dirs = [
  "src/api",
  "src/hooks",
  "src/stores",
  "src/components/chat",
  "src/components/upload",
  "src/components/common",
  "src/types",
  "src/utils",
];

const files = [
  "src/api/client.ts",
  "src/api/chat.service.ts",
  "src/api/document.service.ts",
  "src/hooks/useChatStream.ts",
  "src/hooks/useTaskPolling.ts",
  "src/stores/auth.store.ts",
  "src/stores/chat.store.ts",
  "src/types/api.d.ts",
];

async function ensureStructure() {
  for (const dir of dirs) {
    await mkdir(path.join(root, dir), { recursive: true });
  }

  for (const file of files) {
    const fullPath = path.join(root, file);
    await writeFile(fullPath, "", { encoding: "utf-8", flag: "a" });
  }
}

ensureStructure()
  .then(() => {
    console.log("Scaffold completed.");
  })
  .catch((err) => {
    console.error("Scaffold failed:", err);
    process.exitCode = 1;
  });
