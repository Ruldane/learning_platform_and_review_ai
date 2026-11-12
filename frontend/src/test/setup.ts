import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

// jsdom n'a pas de `ResizeObserver`, que React Flow et Recharts exigent. Ce faux ne notifie jamais
// de mesure : les composants rendent avec les dimensions qu'on leur donne (voir `SkillGraph`).
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
globalThis.ResizeObserver ??= ResizeObserverStub;

// Recharts (`ResponsiveContainer`) mesure son conteneur avec `getBoundingClientRect`, toujours vide
// dans jsdom : sans taille, aucun graphique ne se dessine. Les conteneurs de graphiques en reçoivent une.
const measure = Element.prototype.getBoundingClientRect;
Element.prototype.getBoundingClientRect = function getBoundingClientRect(this: Element) {
  return this.classList.contains("recharts-responsive-container")
    ? new DOMRect(0, 0, 480, 360)
    : measure.call(this);
};

// Aucune requête réseau réelle : toute requête sans handler fait échouer le test.
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
