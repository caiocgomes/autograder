# Frontend - Autograder Web

React + TypeScript + Vite frontend for code submission and grading.

## Commands

```bash
npm install        # Install deps
npm run dev        # Vite dev server (port 5173)
npm run build      # TypeScript check + Vite production build
npm run lint       # ESLint
npm run preview    # Preview production build
```

## Configuration

- Node.js 18+ with npm
- `VITE_API_URL` env var to set backend URL (defaults to `http://localhost:8000`)

## Architecture

- **API client** (`src/api/client.ts`): Axios with JWT auto-refresh and request queuing during token renewal. Domain-specific API modules in `src/api/` (classes, exercises, submissions, grades).
- **Auth state** (`src/store/authStore.ts`): Zustand store. Tokens stored in localStorage.
- **Routing** (`src/App.tsx`): React Router v6. `ProtectedRoute` checks auth + role. Professor routes at `/professor/*`, student routes at `/student/*`.
- **Layouts**: `ProfessorLayout` and `StudentLayout` with sidebar nav, render children via `<Outlet />`.
- **Styling**: Inline styles, no CSS framework or component library.
