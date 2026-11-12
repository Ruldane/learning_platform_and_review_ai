import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import { excalidrawFonts } from "./vite.excalidraw-fonts.ts";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), excalidrawFonts()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
});
