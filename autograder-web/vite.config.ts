import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_TARGET = process.env.VITE_API_URL || 'http://localhost:8000'

const apiPrefixes = [
  '/auth',
  '/users',
  '/classes',
  '/exercises',
  '/exercise-lists',
  '/submissions',
  '/grades',
  '/webhooks',
  '/products',
  '/admin',
  '/messaging',
  '/docs',
  '/openapi.json',
]

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      apiPrefixes.map((prefix) => [
        prefix,
        { target: API_TARGET, changeOrigin: true },
      ])
    ),
  },
})
