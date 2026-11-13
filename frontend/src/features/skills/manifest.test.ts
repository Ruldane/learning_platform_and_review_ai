import { describe, expect, it } from "vitest";
import { skillsManifest } from "./manifest";

describe("skillsManifest", () => {
  it("declares the map route in full width and its entry in the skills section", () => {
    expect(skillsManifest.id).toBe("skills");
    expect(skillsManifest.routes.map((route) => route.path)).toEqual(["competences"]);
    expect(skillsManifest.routes[0]?.handle).toEqual({ wide: true });
    expect(skillsManifest.nav).toEqual([
      { section: "skills", labelKey: "skills.nav.map", path: "/competences", order: 1 },
    ]);
  });
});
