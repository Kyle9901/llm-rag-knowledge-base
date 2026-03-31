# RAG Frontend

React 18 + TypeScript + Vite frontend for the FastAPI RAG backend.

## Quick Start

```bash
npm install
cp .env.example .env.local
npm run dev
```

Default dev URL: `http://127.0.0.1:5173`

## Environment

- `VITE_API_BASE_URL`: backend base URL, default `http://127.0.0.1:8000`

## Engineering Commands

```bash
npm run lint
npm run typecheck
npm run build
npm run format
```

## Husky

Run once after install:

```bash
npm run prepare
npx husky init
```
