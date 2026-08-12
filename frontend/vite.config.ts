import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

/**
 * Vite 配置：开发服务器将 /api 请求代理到后端 FastAPI（8000 端口）。
 */
export default defineConfig({
  plugins: [vue()],
  server: {
    // 默认只监听本机；Docker 容器内通过 VITE_HOST=0.0.0.0 覆盖
    host: process.env.VITE_HOST || "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
