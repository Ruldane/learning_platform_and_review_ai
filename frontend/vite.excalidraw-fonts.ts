import { createReadStream, existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import type { Plugin } from "vite";

/** Où le front sert les polices d'Excalidraw (`window.EXCALIDRAW_ASSET_PATH` + `fonts/…`). */
export const EXCALIDRAW_ASSET_URL = "/excalidraw-assets/";

const FONTS_DIR = fileURLToPath(
  new URL("./node_modules/@excalidraw/excalidraw/dist/prod/fonts", import.meta.url),
);
// Xiaolai (13 Mo) ne sert qu'aux caractères chinois : Excalidraw ne la demande qu'à la volée.
const SKIPPED_FAMILIES = new Set(["Xiaolai"]);

function listFonts(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    if (SKIPPED_FAMILIES.has(name)) return [];
    const path = join(dir, name);
    return statSync(path).isDirectory() ? listFonts(path) : [path];
  });
}

/**
 * Sert les polices d'Excalidraw depuis `node_modules` (dev) et les copie dans `dist` (build) :
 * le tableau ne dépend pas d'un CDN (hors ligne, SPEC 17.1). Excalidraw ne retombe sur son CDN
 * que si une police locale manque.
 */
export function excalidrawFonts(): Plugin {
  const prefix = `${EXCALIDRAW_ASSET_URL}fonts/`;
  return {
    name: "tremplin:excalidraw-fonts",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = (req.url ?? "").split("?")[0] ?? "";
        const file = url.startsWith(prefix)
          ? join(FONTS_DIR, decodeURIComponent(url.slice(prefix.length)))
          : "";
        if (!file || !file.startsWith(FONTS_DIR) || !existsSync(file) || !statSync(file).isFile()) {
          next();
          return;
        }
        res.setHeader("Content-Type", "font/woff2");
        createReadStream(file).pipe(res);
      });
    },
    generateBundle() {
      for (const file of listFonts(FONTS_DIR)) {
        const name = relative(FONTS_DIR, file).split(sep).join("/");
        this.emitFile({
          type: "asset",
          fileName: `${prefix.slice(1)}${name}`,
          source: readFileSync(file),
        });
      }
    },
  };
}
