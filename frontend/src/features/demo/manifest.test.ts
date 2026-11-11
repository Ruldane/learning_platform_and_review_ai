import { describe, expect, it } from "vitest";
import { demoManifest } from "./manifest";

describe("demoManifest", () => {
  it("expose /demo sans entrée de navigation", () => {
    expect(demoManifest.id).toBe("demo");
    expect(demoManifest.routes.map((route) => route.path)).toEqual(["/demo"]);
    expect(demoManifest.nav ?? []).toEqual([]);
  });
});
