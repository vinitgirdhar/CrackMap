# CrackMap Frontend (Next.js 16 App Router)

Modern, high-performance web interface for the **CrackMap Road Damage & Pothole Detection System**. Built with Next.js 16, React 19, TypeScript, and custom CSS design tokens.

---

## 🚀 Development Setup

### 1. Ensure Backend is Running
In the repository root or backend directory:
```bash
# Terminal 1: Start FastAPI backend (port 8000)
python -m uvicorn backend.app.main:app --port 8000
```

### 2. Start Frontend Dev Server
```bash
# Terminal 2: Start Next.js frontend (port 3000)
cd front-end
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing & Validation Suite

```bash
# Run Vitest unit & API hook tests (24 passed)
npm test

# Run Playwright end-to-end browser tests
npm run e2e

# Run Next.js production build and TypeScript typecheck
npm run build

# Run ESLint validation
npm run lint
```

---

## 📁 Component Structure

- `app/`: Next.js App Router root layout, page component, and global CSS.
- `components/`:
  - `DetectorView.tsx`: Core inspection workspace with live image upload/sample presets and scoring methodology card.
  - `AnalyticsView.tsx`: Professional Kaggle dataset profile, split breakdown, and model benchmark evaluation dashboard.
  - `HeroSection.tsx`: Live telemetry stat strip.
  - `TopNavBar.tsx`: Brand navigation with real-time global refresh button.
  - `FilterControlsPopover.tsx`: Interactive AI confidence and IoU overlap sliders.
  - `SettingsModal.tsx`: Visual overlay and telemetry preferences.
- `lib/`: Typed API client (`api.ts`), custom hooks, and shared interfaces (`types.ts`).
- `e2e/`: Playwright browser test specs.
