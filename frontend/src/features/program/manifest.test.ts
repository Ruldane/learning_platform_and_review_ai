import { describe, expect, it } from "vitest";
import { programManifest } from "./manifest";

describe("programManifest", () => {
  it("declares Programme under Apprendre, after Objectifs and Conseil", () => {
    expect(programManifest.id).toBe("program");
    expect(programManifest.nav).toEqual([
      { section: "learn", labelKey: "program.nav.program", path: "/apprendre/programme", order: 3 },
    ]);
  });

  it("declares the latest-program route and the one with an identifier, wide", () => {
    expect(programManifest.routes.map((route) => route.path)).toEqual([
      "apprendre/programme",
      "apprendre/programme/:programId",
    ]);
    expect(programManifest.routes[1]?.handle).toEqual({ wide: true });
  });
});
