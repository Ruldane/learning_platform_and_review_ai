import { describe, expect, it } from "vitest";
import { studyManifest } from "./manifest";

describe("studyManifest", () => {
  it("declares the guided session routes, its entry and the top bar slot", () => {
    expect(studyManifest.id).toBe("study");
    expect(studyManifest.routes.map((route) => route.path)).toEqual([
      "study/session",
      "study/session/:studyId",
    ]);
    expect(studyManifest.routes[1]?.handle).toEqual({ wide: true });
    expect(studyManifest.nav).toEqual([
      { section: "study", labelKey: "study.nav.session", path: "/study/session", order: 1 },
    ]);
    expect(studyManifest.shell?.topbar).toBeDefined();
  });
});
