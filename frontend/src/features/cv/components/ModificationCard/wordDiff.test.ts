import { describe, expect, it } from "vitest";
import { wordDiff } from "./wordDiff";

describe("wordDiff", () => {
  it("keeps common words, marks the removed and the added", () => {
    expect(wordDiff("Gère une équipe de 4 personnes", "Dirige une équipe de 4 personnes")).toEqual([
      { kind: "del", text: "Gère" },
      { kind: "add", text: "Dirige" },
      { kind: "same", text: "une équipe de 4 personnes" },
    ]);
  });

  it("returns a single block of same words when nothing changed", () => {
    expect(wordDiff("a b  c", "a b c")).toEqual([{ kind: "same", text: "a b c" }]);
  });

  it("handles an empty side", () => {
    expect(wordDiff("", "Nouvelle ligne")).toEqual([{ kind: "add", text: "Nouvelle ligne" }]);
    expect(wordDiff("Ancienne ligne", "")).toEqual([{ kind: "del", text: "Ancienne ligne" }]);
    expect(wordDiff("", "")).toEqual([]);
  });

  it("gives a huge text as one removal and one addition instead of building a huge table", () => {
    const before = Array.from({ length: 800 }, (_, i) => `a${i}`).join(" ");
    const after = Array.from({ length: 800 }, (_, i) => `b${i}`).join(" ");
    expect(wordDiff(before, after).map((segment) => segment.kind)).toEqual(["del", "add"]);
  });
});
