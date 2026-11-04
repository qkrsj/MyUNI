import { resolve } from 'node:path';
import { defineConfig } from 'electron-vite';

// @myuni/shared 는 TS 소스 패키지라 번들에 포함시킨다 (zod 도 함께)
const bundled = { exclude: ['@myuni/shared', 'zod'] };

export default defineConfig({
  main: {
    build: { externalizeDeps: bundled },
  },
  preload: {
    build: { externalizeDeps: bundled },
  },
  renderer: {
    build: {
      rollupOptions: {
        input: {
          pet: resolve(__dirname, 'src/renderer/pet.html'),
          login: resolve(__dirname, 'src/renderer/login.html'),
        },
      },
    },
  },
});
