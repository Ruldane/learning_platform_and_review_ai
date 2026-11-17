import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/errors";
import { isRefused, refusedFields } from "./refusedFields";

const refusal = (details: unknown, status = 422) =>
  new ApiError({ code: "validation_error", message: "Requête invalide.", status, details });

describe("refusedFields", () => {
  it("reads the field paths of a 422, and nothing else", () => {
    expect(refusedFields(refusal({ fields: ["agent_overrides", "brief_time"] }))).toEqual([
      "agent_overrides",
      "brief_time",
    ]);
    expect(refusedFields(refusal({ fields: ["brief_time", 3, null] }))).toEqual(["brief_time"]);
    expect(refusedFields(refusal(null))).toEqual([]);
    expect(refusedFields(refusal({ fields: "brief_time" }))).toEqual([]);
    expect(refusedFields(refusal({ fields: ["brief_time"] }, 500))).toEqual([]);
    expect(refusedFields(new Error("boom"))).toEqual([]);
    expect(refusedFields(null)).toEqual([]);
  });

  it("matches a field itself and its sub-fields, never a longer name", () => {
    expect(isRefused(["agent_overrides.tutor.model"], "agent_overrides")).toBe(true);
    expect(isRefused(["agent_overrides"], "agent_overrides")).toBe(true);
    expect(isRefused(["agent_overrides_x"], "agent_overrides")).toBe(false);
    expect(isRefused([], "agent_overrides")).toBe(false);
  });
});
