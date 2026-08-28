import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 7432,
    proxy: {
      "/api": {
        target: "http://localhost:9147",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
