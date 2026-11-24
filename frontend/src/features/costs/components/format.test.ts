import { describe, expect, it } from "vitest";
import { formatCallTime, formatUsd, formatUsdTick } from "./format";

describe("formatUsd", () => {
  it("writes a positive cost below a mill as < $0.001", () => {
    expect(formatUsd(0.00038)).toBe("< $0.001");
    expect(formatUsd(0.0000001)).toBe("< $0.001");
  });

  it("keeps three decimals under a cent and two for cents or zero", () => {
    expect(formatUsd(0.004)).toBe("$0.004");
    expect(formatUsd(0.42)).toBe("$0.42");
    expect(formatUsd(0)).toBe("$0.00");
  });

  it("groups thousands and puts the dollar sign before the amount", () => {
    expect(formatUsd(1_234.5)).toBe("$1,234.50");
  });
});

describe("formatUsdTick", () => {
  it("keeps every tick of a very cheap window different, with enough decimals", () => {
    const ticks = [0, 0.0001, 0.0002, 0.0003, 0.0004].map(formatUsdTick);
    expect(new Set(ticks).size).toBe(5);
    expect(ticks[1]).toBe("$0.0001");
    expect(ticks.join(" ")).not.toContain("<");
  });

  it("writes ordinary ticks like a cost", () => {
    expect(formatUsdTick(0)).toBe("$0.00");
    expect(formatUsdTick(0.5)).toBe("$0.50");
    expect(formatUsdTick(12)).toBe("$12.00");
  });
});

describe("formatCallTime", () => {
  it("adds the year only when it is not the current one", () => {
    const now = new Date();
    const thisYear = new Date(now.getFullYear(), 5, 15, 10, 30).toISOString();
    const older = new Date(now.getFullYear() - 1, 5, 15, 10, 30).toISOString();
    expect(formatCallTime(thisYear)).not.toContain(String(now.getFullYear()));
    expect(formatCallTime(older)).toContain(String(now.getFullYear() - 1));
  });
});
