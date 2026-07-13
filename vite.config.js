import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // O Vite carrega automaticamente as variáveis do sistema (incluindo as da Vercel)
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react()],
    // Garante que o diretório de saída seja o padrão esperado pela Vercel
    build: {
      outDir: 'dist',
    },
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: true, // Em produção (HTTPS), melhor deixar como true
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})

