import { describe, expect, it } from "vitest";
import { formatCallTime, formatUsd } from "./format";

describe("formatUsd", () => {
  it("writes a cost between zero and a mill as « < 0,001 $ », never « 0,000 $ »", () => {
    expect(formatUsd(0.00038)).toBe("< 0,001\u00a0$");
    expect(formatUsd(0.0000001)).toBe("< 0,001\u00a0$");
  });

  it("keeps three decimals under a cent and two above, and writes a real zero as 0,00", () => {
    expect(formatUsd(0.004)).toBe("0,004\u00a0$");
    expect(formatUsd(0.42)).toBe("0,42\u00a0$");
    expect(formatUsd(0)).toBe("0,00\u00a0$");
  });

  it("uses a non-breaking space before the dollar sign", () => {
    expect(formatUsd(12.5)).toMatch(/\u00a0\$$/);
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
