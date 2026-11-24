import type { FeatureManifest } from "@/shared/lib/feature";
import { DocumentsPage } from "./pages/DocumentsPage";
import { MemoryExplorerPage } from "./pages/MemoryExplorerPage";
import { MemoryMapPage } from "./pages/MemoryMapPage";
import { SearchBenchPage } from "./pages/SearchBenchPage";

/** Mémoire (F3) : explorateur, carte 2D, banc d'essai et documents, section « Mémoire » (15.1). */
export const memoryManifest: FeatureManifest = {
  id: "memory",
  routes: [
    { path: "memory", Component: MemoryExplorerPage },
    { path: "memory/map", Component: MemoryMapPage },
    { path: "memory/search-bench", Component: SearchBenchPage },
    { path: "memory/documents", Component: DocumentsPage },
  ],
  nav: [
    { section: "memory", labelKey: "memory.nav.explorer", path: "/memory", order: 1 },
    { section: "memory", labelKey: "memory.nav.map", path: "/memory/map", order: 2 },
    { section: "memory", labelKey: "memory.nav.bench", path: "/memory/search-bench", order: 3 },
    { section: "memory", labelKey: "memory.nav.documents", path: "/memory/documents", order: 4 },
  ],
};
