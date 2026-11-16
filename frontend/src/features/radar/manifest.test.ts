import { describe, expect, it } from "vitest";
import { radarManifest } from "./manifest";

describe("radarManifest", () => {
  it("declares the two routes and one entry in Carrière, order 5, « Radar »", () => {
    expect(radarManifest.id).toBe("radar");
    expect(radarManifest.routes.map((route) => route.path)).toEqual([
      "carriere/radar",
      "carriere/radar/:runId",
    ]);
    expect(radarManifest.nav).toEqual([
      { section: "career", labelKey: "radar.nav.radar", path: "/carriere/radar", order: 5 },
    ]);
  });
});
