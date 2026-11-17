import { fileURLToPath } from "node:url";
import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.ts";

const fake = (name: string) => fileURLToPath(new URL(`./src/test/${name}`, import.meta.url));

export default mergeConfig(
  viteConfig,
  defineConfig({
    resolve: {
      // Monaco ne tourne pas sous jsdom : l'éditeur et le paquet sont remplacés par des faux
      // (`src/test/fakeMonaco*`). L'alias couvre `monaco-editor`, ses sous-chemins et `?worker`.
      alias: [
        { find: /^@monaco-editor\/react$/, replacement: fake("fakeMonacoReact.tsx") },
        { find: /^monaco-editor(\/.*)?$/, replacement: fake("fakeMonacoEditor.ts") },
      ],
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"],
      css: false,
    },
  }),
);
