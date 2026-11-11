import { describe, expect, it } from "vitest";
import { formatShare, MAX_UPLOAD_BYTES } from "./format";

describe("format", () => {
  it("formatShare formats a percentage in French", () => {
    expect(formatShare(0.25)).toBe("25,0 %");
    expect(formatShare(0)).toBe("0,0 %");
    expect(formatShare(0.0123)).toBe("1,2 %");
  });

  it("caps uploads at 20 MB", () => {
    expect(MAX_UPLOAD_BYTES).toBe(20 * 1024 * 1024);
  });
});
