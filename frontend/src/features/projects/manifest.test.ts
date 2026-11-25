import { describe, expect, it } from "vitest";
import { projectsManifest } from "./manifest";

describe("projectsManifest", () => {
  it("declares the two routes and one entry in Compétences, order 2, « Portfolio »", () => {
    expect(projectsManifest.id).toBe("projects");
    expect(projectsManifest.routes.map((route) => route.path)).toEqual([
      "skills/portfolio",
      "skills/portfolio/:projectId",
    ]);
    expect(projectsManifest.nav).toEqual([
      {
        section: "skills",
        labelKey: "projects.nav.portfolio",
        path: "/skills/portfolio",
        order: 2,
      },
    ]);
  });
});
