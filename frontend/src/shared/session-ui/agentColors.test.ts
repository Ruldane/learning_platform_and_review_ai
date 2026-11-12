import { describe, expect, it } from "vitest";
import { AGENT_COLORS, agentIdentity } from "./agentColors";

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const v = parseInt(hex.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

describe("agentColors", () => {
  it("falls back for unknown slugs", () => {
    const identity = agentIdentity("x");
    expect(identity.name).toBe("x");
    expect(identity.role).toBe("");
    expect(identity.color).toMatch(/^#[0-9a-f]{6}$/);
  });

  it("does not resolve inherited object keys as agents", () => {
    expect(agentIdentity("constructor").name).toBe("constructor");
  });

  it("every reserved agent has a distinct color", () => {
    expect(new Set(Object.values(AGENT_COLORS)).size).toBe(Object.keys(AGENT_COLORS).length);
  });

  it("reserves all the slugs of the roadmap", () => {
    expect(Object.keys(AGENT_COLORS)).toHaveLength(19);
    expect(Object.keys(AGENT_COLORS)).toContain("demo_critic");
    expect(Object.keys(AGENT_COLORS)).toContain("ats_reader");
  });

  it("every color reaches AA contrast on the off-white background", () => {
    for (const color of Object.values(AGENT_COLORS)) {
      expect(contrast(color, "#fafaf7")).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("knows examiner and tutor", () => {
    const examiner = agentIdentity("examiner");
    expect(examiner).toMatchObject({ name: "Examinateur", color: AGENT_COLORS.examiner });
    expect(examiner.role).not.toBe("");
    const tutor = agentIdentity("tutor");
    expect(tutor).toMatchObject({ name: "Tuteur", color: AGENT_COLORS.tutor });
    expect(tutor.role).not.toBe("");
    for (const color of [examiner.color, tutor.color]) {
      expect(contrast(color, "#fafaf7")).toBeGreaterThanOrEqual(4.5);
      expect(contrast(color, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("resolves name and role from the French messages", () => {
    const identity = agentIdentity("demo_critic");
    expect(identity.name).toBe("Critique");
    expect(identity.role).not.toBe("");
    expect(identity.color).toBe(AGENT_COLORS.demo_critic);
  });
});
