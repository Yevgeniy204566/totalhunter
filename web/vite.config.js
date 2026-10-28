import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      // clan.html — страница нейтрального домена, свой бандл только с публичными маршрутами
      input: {
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        clan: fileURLToPath(new URL('./clan.html', import.meta.url)),
      },
    },
  },
})
