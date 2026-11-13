import { describe, expect, it } from "vitest";
import layoutSource from "./components/layoutGraph.ts?raw";
import manifestSource from "./manifest.ts?raw";
import { skillsManifest } from "./manifest";

/**
 * Revue finale 5 (C-m4) : elkjs, Recharts et React Flow ne doivent pas entrer dans le paquet
 * principal. La page est chargée à l'ouverture de la route, elkjs à la première mise en page.
 * (Vérifié aussi sur le paquet construit : `pnpm build`.)
 */
describe("skills bundle", () => {
  it("loads the map page lazily", async () => {
    const route = skillsManifest.routes[0]!;
    expect(route.Component).toBeUndefined();
    expect(manifestSource).not.toMatch(/^import .*pages\/SkillsPage/m);
    expect(typeof route.lazy).toBe("function");
    const loaded = await (route.lazy as () => Promise<{ Component: unknown }>)();
    expect(typeof loaded.Component).toBe("function");
  }, 30_000); // la première transformation de la page (React Flow, Recharts) est longue

  it("imports elkjs only when a layout is needed", () => {
    expect(layoutSource).not.toMatch(/^import .*elkjs/m);
    expect(layoutSource).toMatch(/import\("elkjs\/lib\/elk\.bundled\.js"\)/);
  });
});
