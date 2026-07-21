import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  // Tauri shows its own errors; don't let Vite wipe the terminal.
  clearScreen: false,
  // strictPort: a port conflict must fail loudly, not silently move —
  // Tauri points at 1420 and would otherwise load a blank window.
  server: { port: 1420, strictPort: true },
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
