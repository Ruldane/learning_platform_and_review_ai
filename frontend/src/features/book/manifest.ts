import type { FeatureManifest } from "@/shared/lib/feature";
import { BookPage } from "./pages/BookPage";

export const bookManifest: FeatureManifest = {
  id: "book",
  routes: [{ path: "learn/book/:programId?", Component: BookPage }],
  nav: [{ section: "learn", labelKey: "book.title", path: "/learn/book", order: 6 }],
};
