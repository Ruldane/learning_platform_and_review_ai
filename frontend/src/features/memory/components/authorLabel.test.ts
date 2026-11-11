import { describe, expect, it } from "vitest";
import { authorLabel } from "./authorLabel";
import { formatScore } from "./formatScore";

describe("authorLabel", () => {
  it("maps user to Toi", () => {
    expect(authorLabel("user")).toBe("Toi");
  });

  it("uses the agent name otherwise", () => {
    expect(authorLabel("archivist")).toBe("Archiviste");
  });

  it("falls back to the slug for an unknown author", () => {
    expect(authorLabel("inconnu")).toBe("inconnu");
  });
});

describe("formatScore", () => {
  it("uses a French decimal comma", () => {
    expect(formatScore(0.834)).toBe("0,83");
  });

  it("always shows two decimals", () => {
    expect(formatScore(1)).toBe("1,00");
    expect(formatScore(0)).toBe("0,00");
  });
});
