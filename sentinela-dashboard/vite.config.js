import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      usePolling: true, // Importante para ambientes virtualizados (VMware)
    },
    hmr: {
      overlay: false,
    }
  },
  build: {
    // Isso impede que o Vite tente deletar a pasta de relatórios
    // durante o processo de build, evitando o erro de diretório
    emptyOutDir: false,
  }
})
