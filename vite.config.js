import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'designed_vue_app/public/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'frontend/main.js'),
      output: {
        format: 'iife',
        name: 'DesignedVueApp',
        entryFileNames: 'js/designed_vue_app.js',
        assetFileNames: 'css/designed_vue_app.[ext]'
      }
    }
  }
});
