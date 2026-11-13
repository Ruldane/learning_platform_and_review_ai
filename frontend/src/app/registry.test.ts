import { describe, expect, it } from "vitest";
import { buildNav } from "./buildNav";
import { FEATURES } from "./registry";

describe("registre des features", () => {
  it("a des identifiants uniques", () => {
    const ids = FEATURES.map((f) => f.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("expose l'accueil, Apprendre, Étudier, la mémoire et les réglages dans la navigation", () => {
    const groups = buildNav(FEATURES);
    expect(groups.map((g) => g.section)).toEqual(["home", "learn", "study", "memory", "settings"]);
    expect(groups[0]?.items).toEqual([{ labelKey: "nav.home", path: "/" }]);
    expect(groups[1]?.items.map((item) => item.path)).toEqual([
      "/apprendre/objectifs",
      "/apprendre/conseil",
      "/apprendre/programme",
      "/apprendre/lecons",
      "/apprendre/bibliotheque",
    ]);
    expect(groups[2]?.items.map((item) => item.path)).toEqual([
      "/etudier/session",
      "/etudier/revisions",
      "/etudier/quiz",
    ]);
    expect(groups[3]?.items.map((item) => item.path)).toEqual([
      "/memoire",
      "/memoire/carte",
      "/memoire/banc",
      "/memoire/documents",
    ]);
    expect(groups[4]?.items).toEqual([
      { labelKey: "settings.models.navLabel", path: "/reglages/modeles" },
      { labelKey: "settings.search.navLabel", path: "/reglages/recherche" },
      { labelKey: "research.nav.bench", path: "/reglages/recherche/essai" },
      { labelKey: "settings.study.navLabel", path: "/reglages/etude" },
    ]);
  });
});
