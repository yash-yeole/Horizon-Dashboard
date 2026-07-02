---
title: Horizon Frontend
emoji: ⚡
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# HORIZON Energy Terminal — Frontend

Vite + React + TypeScript dashboard, built and served as a static site (nginx) on
port 7860. The API base URL is inlined at build time from `.env.production`
(`VITE_API_BASE_URL` → the HORIZON backend Space).

Deployed automatically from the `energy-dashboard/` subtree of the repo by the
`Sync to Hugging Face Spaces` GitHub Action (`.github/workflows/sync.yml`).

## Local development

```bash
npm install
npm run dev      # Vite dev server on :5173, proxies /api -> http://localhost:8000
npm run build    # production build into dist/
```
