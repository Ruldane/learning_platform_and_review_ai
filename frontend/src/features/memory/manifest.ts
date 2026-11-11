import type { FeatureManifest } from "@/shared/lib/feature";
import { DocumentsPage } from "./pages/DocumentsPage";
import { MemoryExplorerPage } from "./pages/MemoryExplorerPage";
import { MemoryMapPage } from "./pages/MemoryMapPage";
import { SearchBenchPage } from "./pages/SearchBenchPage";

/** Mémoire (F3) : explorateur, carte 2D, banc d'essai et documents, section « Mémoire » (15.1). */
export const memoryManifest: FeatureManifest = {
  id: "memory",
  routes: [
    { path: "memoire", Component: MemoryExplorerPage },
    { path: "memoire/carte", Component: MemoryMapPage },
    { path: "memoire/banc", Component: SearchBenchPage },
    { path: "memoire/documents", Component: DocumentsPage },
  ],
  nav: [
    { section: "memory", labelKey: "memory.nav.explorer", path: "/memoire", order: 1 },
    { section: "memory", labelKey: "memory.nav.map", path: "/memoire/carte", order: 2 },
    { section: "memory", labelKey: "memory.nav.bench", path: "/memoire/banc", order: 3 },
    { section: "memory", labelKey: "memory.nav.documents", path: "/memoire/documents", order: 4 },
  ],
};
