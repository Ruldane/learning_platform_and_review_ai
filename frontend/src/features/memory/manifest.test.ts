import { describe, expect, it } from "vitest";
import { t } from "@/shared/i18n/t";
import { memoryManifest } from "./manifest";

describe("memoryManifest", () => {
  it("declares the four memory screens", () => {
    expect(memoryManifest.id).toBe("memory");
    expect(memoryManifest.nav?.map((n) => n.path)).toEqual([
      "/memoire",
      "/memoire/carte",
      "/memoire/banc",
      "/memoire/documents",
    ]);
    expect(memoryManifest.routes.map((r) => r.path)).toEqual([
      "memoire",
      "memoire/carte",
      "memoire/banc",
      "memoire/documents",
    ]);
  });

  it("puts every entry in the memory section, in order, with the labels of SPEC 15.1", () => {
    const nav = memoryManifest.nav ?? [];
    expect(nav.every((n) => n.section === "memory")).toBe(true);
    expect(nav.map((n) => n.order)).toEqual([1, 2, 3, 4]);
    expect(nav.map((n) => t(n.labelKey))).toEqual([
      "Explorateur",
      "Carte 2D",
      "Banc d'essai",
      "Documents",
    ]);
  });
});
