import { describe, expect, it } from "vitest";
import { row } from "../viewFixtures";
import { canMerge } from "./mergeRule";

describe("canMerge", () => {
  it("needs two items or more", () => {
    expect(canMerge([row({ id: "a" })])).toBe(false);
    expect(canMerge([])).toBe(false);
  });

  it("accepts two items of the same kind", () => {
    expect(canMerge([row({ id: "a" }), row({ id: "b" })])).toBe(true);
  });

  it("refuses mixed kinds", () => {
    expect(canMerge([row({ id: "a" }), row({ id: "b", kind: "decision" })])).toBe(false);
  });

  it("refuses documents", () => {
    expect(canMerge([row({ kind: "document" }), row({ id: "b", kind: "document" })])).toBe(false);
  });
});
