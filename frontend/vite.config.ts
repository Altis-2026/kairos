import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const VENDOR_GROUPS: [string, string[]][] = [
  ["mapbox", ["mapbox-gl"]],
  ["firebase", ["firebase", "@firebase"]],
  ["react", ["react", "react-dom", "scheduler", "zustand", "@tanstack"]],
  ["ui", ["framer-motion", "lucide-react"]],
];

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    target: "es2021",
    chunkSizeWarningLimit: 1800,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          for (const [name, packages] of VENDOR_GROUPS) {
            if (packages.some((p) => id.includes(`/node_modules/${p}/`))) return `vendor-${name}`;
          }
          return "vendor";
        },
      },
    },
  },
});
