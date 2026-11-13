import { describe, expect, it } from "vitest";
import { replanManifest } from "./manifest";

describe("replanManifest", () => {
  it("declares the replan route of a program and no navigation entry", () => {
    expect(replanManifest.id).toBe("replan");
    expect(replanManifest.routes.map((route) => route.path)).toEqual([
      "apprendre/programme/:programId/replanification",
    ]);
    expect(replanManifest.nav).toBeUndefined();
  });
});
