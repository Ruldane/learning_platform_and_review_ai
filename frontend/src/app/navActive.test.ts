import { Home } from "lucide-react";
import { describe, expect, it } from "vitest";
import type { NavGroup } from "./buildNav";
import { currentNav } from "./navActive";

const base = { icon: Home } as const;
const groups: NavGroup[] = [
  { ...base, section: "home", labelKey: "nav.home", items: [{ labelKey: "nav.home", path: "/" }] },
  {
    ...base,
    section: "applications",
    labelKey: "nav.applications",
    items: [
      { labelKey: "applications.nav.board", path: "/candidatures" },
      { labelKey: "applications.nav.reminders", path: "/candidatures/relances" },
    ],
  },
];

describe("currentNav", () => {
  it("n'active « / » que sur l'accueil", () => {
    expect(currentNav(groups, "/")).toEqual({ section: "home", path: "/" });
    expect(currentNav(groups, "/ailleurs")).toBeNull();
  });

  it("garde l'entrée la plus générale sur une sous-route hors navigation (fiche ouverte)", () => {
    expect(currentNav(groups, "/candidatures/a1")).toEqual({
      section: "applications",
      path: "/candidatures",
    });
  });

  it("préfère l'entrée la plus précise quand l'une est la sous-route de l'autre", () => {
    expect(currentNav(groups, "/candidatures/relances")).toEqual({
      section: "applications",
      path: "/candidatures/relances",
    });
  });
});
