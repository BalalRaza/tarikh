import { defineConfig } from 'vite';

export default defineConfig({
  base: '/tarikh/',
  build: { outDir: 'dist', target: 'es2020' },
});
