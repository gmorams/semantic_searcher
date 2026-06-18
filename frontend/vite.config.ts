import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En dev redirigimos /api al backend FastAPI (puerto 8000); en build el front
// se sirve via nginx que tambien proxa /api hacia el contenedor api.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
