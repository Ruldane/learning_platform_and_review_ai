import { describe, expect, it, vi } from "vitest";
import { getEventRenderer, registerEventRenderer, type EventRenderer } from "./eventRenderers";

// Deux composants distincts sans en déclarer deux dans le fichier (react/no-multi-comp).
const renderer = (): EventRenderer => vi.fn(() => null);
const SourceCard = renderer();
const OtherCard = renderer();

describe("eventRenderers", () => {
  it("returns undefined for an unregistered type and the component once registered", () => {
    expect(getEventRenderer("source.found")).toBeUndefined();
    const unregister = registerEventRenderer("source.found", SourceCard);
    expect(getEventRenderer("source.found")).toBe(SourceCard);
    expect(getEventRenderer("board.update")).toBeUndefined();
    unregister();
    expect(getEventRenderer("source.found")).toBeUndefined();
  });

  it("replaces a renderer, and a stale unregister leaves the new one in place", () => {
    const first = registerEventRenderer("artifact.ready", SourceCard);
    const second = registerEventRenderer("artifact.ready", OtherCard);
    first();
    expect(getEventRenderer("artifact.ready")).toBe(OtherCard);
    second();
    expect(getEventRenderer("artifact.ready")).toBeUndefined();
  });
});
