# Frontend - Autograder Web

React + TypeScript + Vite frontend para submissão de código.

## Commands

```bash
npm install          # Install dependencies
npm run dev          # Start Vite dev server
npm run build        # TypeScript + Vite production build
npm run lint         # ESLint check
```

## Structure

- `src/App.tsx` - Main component with form state management
- `src/api/grader.ts` - HTTP client for `/grade` endpoint
- `src/components/` - CodeEditor, TestCases, Results components

## Configuration

- Node.js with npm
- `VITE_API_URL` to override API endpoint (defaults to relative `/grade`)
