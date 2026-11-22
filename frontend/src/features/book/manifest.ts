import type { FeatureManifest } from "@/shared/lib/feature";
import { BookPage } from "./pages/BookPage";

export const bookManifest: FeatureManifest = {
  id: "book",
  routes: [{ path: "apprendre/livre/:programId?", Component: BookPage }],
  nav: [{ section: "learn", labelKey: "book.title", path: "/apprendre/livre", order: 6 }],
};
