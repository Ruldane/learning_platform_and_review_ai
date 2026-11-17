import { describe, expect, it } from "vitest";
import { GRAPH_SCREENS } from "@/features/costs/components/graphs";
import { buildNav } from "./buildNav";
import { FEATURES } from "./registry";

describe("registre des features", () => {
  it("met la connexion en premier : sa porte est la plus extérieure", () => {
    expect(FEATURES[0]?.id).toBe("auth");
    expect(FEATURES[0]?.shell?.gate).toBeDefined();
  });

  it("a des identifiants uniques", () => {
    const ids = FEATURES.map((f) => f.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("expose l'accueil, Apprendre, Étudier, Compétences, Carrière, Candidatures, la mémoire et les réglages dans la navigation", () => {
    const groups = buildNav(FEATURES);
    expect(groups.map((g) => g.section)).toEqual([
      "home",
      "learn",
      "study",
      "skills",
      "career",
      "applications",
      "memory",
      "settings",
    ]);
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
      "/etudier/journal",
      "/code",
    ]);
    expect(groups[3]?.items).toEqual([
      { labelKey: "skills.nav.map", path: "/competences" },
      { labelKey: "projects.nav.portfolio", path: "/competences/portfolio" },
    ]);
    expect(groups[4]?.items).toEqual([
      { labelKey: "cv.nav.profile", path: "/carriere/profil" },
      { labelKey: "cv.nav.cv", path: "/carriere/cv" },
      { labelKey: "gap.nav.postings", path: "/carriere/offres" },
      { labelKey: "gap.nav.overview", path: "/carriere/ecarts" },
      { labelKey: "radar.nav.radar", path: "/carriere/radar" },
    ]);
    expect(groups[5]?.items.map((item) => item.path)).toEqual([
      "/candidatures",
      "/candidatures/relances",
      "/candidatures/entretien",
    ]);
    expect(groups[6]?.items.map((item) => item.path)).toEqual([
      "/memoire",
      "/memoire/carte",
      "/memoire/banc",
      "/memoire/documents",
    ]);
    expect(groups[7]?.items).toEqual([
      { labelKey: "settings.models.navLabel", path: "/reglages/modeles" },
      { labelKey: "settings.search.navLabel", path: "/reglages/recherche" },
      { labelKey: "research.nav.bench", path: "/reglages/recherche/essai" },
      { labelKey: "settings.availability.navLabel", path: "/reglages/disponibilite" },
      { labelKey: "settings.study.navLabel", path: "/reglages/etude" },
      { labelKey: "settings.style.navLabel", path: "/reglages/style" },
      { labelKey: "costs.nav.costs", path: "/reglages/couts" },
      { labelKey: "costs.nav.log", path: "/reglages/journal" },
      { labelKey: "account.nav.data", path: "/reglages/donnees" },
      { labelKey: "mcp.nav.access", path: "/reglages/mcp" },
    ]);
  });

  it("le journal des agents ne mène qu'à des écrans qui existent", () => {
    const known = new Set([
      ...FEATURES.flatMap((f) => f.nav?.map((entry) => entry.path) ?? []),
      ...FEATURES.flatMap((f) =>
        f.routes.map((route) => `/${(route.path ?? "").replace(/^\//, "")}`),
      ),
    ]);
    for (const path of Object.values(GRAPH_SCREENS)) expect(known).toContain(path);
  });
});
