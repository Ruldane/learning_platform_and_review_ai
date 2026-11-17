import { describe, expect, it } from "vitest";
import { fieldClass } from "./fieldClass";

describe("fieldClass", () => {
  it("changes the frame of an invalid field, so the state is not carried by the help text colour alone", () => {
    expect(fieldClass).toContain("aria-invalid:border-destructive");
    expect(fieldClass).toContain("aria-invalid:ring-destructive/20");
  });
});
