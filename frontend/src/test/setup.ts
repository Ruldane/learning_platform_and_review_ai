import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

// jsdom has no `ResizeObserver`, which React Flow and Recharts require. This fake never reports
// a measurement: components render with the dimensions given to them (see `SkillGraph`).
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
globalThis.ResizeObserver ??= ResizeObserverStub;

// Recharts (`ResponsiveContainer`) measures its container with `getBoundingClientRect`, empty
// in jsdom: without a size, no chart is drawn. Chart containers get one.
const measure = Element.prototype.getBoundingClientRect;
Element.prototype.getBoundingClientRect = function getBoundingClientRect(this: Element) {
  return this.classList.contains("recharts-responsive-container")
    ? new DOMRect(0, 0, 480, 360)
    : measure.call(this);
};

// No real network request: any request without a handler makes the test fail.
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
