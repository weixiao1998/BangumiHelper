import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      // import.meta.dirname 取代 __dirname：Vite 8 起原生 config loader 不支持 __dirname
      '@': resolve(import.meta.dirname, 'src'),
    },
  },
  server: {
    host: 'localhost',
    port: 18001,
    allowedHosts: process.env.VITE_ALLOWED_HOSTS?.split(',') || [],
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET || 'http://localhost:18000',
        // 刻意不开启 changeOrigin：后端按请求 Host 生成 RSS 里的站内链接
        // （剧集落地页 /episode/{id}），改写成内部地址会让 feed 里出现 backend:8000
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
