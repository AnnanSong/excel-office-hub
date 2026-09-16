import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// GitHub Pages 默认部署在 /repo-name/ 子路径下
var base = process.env.GITHUB_PAGES_BASE || './';
// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    base: base,
    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
});
