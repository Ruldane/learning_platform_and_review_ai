import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/errors";
import { failureReason, launchErrors, openRunId } from "./errors";

const refusal = (code: string, status: number, details: unknown = null) =>
  new ApiError({ code, message: "Server message.", status, details });

describe("openRunId", () => {
  it("reads the running run of a 409 radar_in_progress", () => {
    expect(openRunId(refusal("radar_in_progress", 409, { run_id: "r9" }))).toBe("r9");
  });

  it("ignores any other refusal and a 409 without an identifier", () => {
    expect(openRunId(refusal("radar_role_required", 409))).toBeNull();
    expect(openRunId(refusal("radar_in_progress", 409, {}))).toBeNull();
    expect(openRunId(new Error("Network error"))).toBeNull();
  });
});

describe("launchErrors", () => {
  it("puts a missing role on the role field", () => {
    expect(launchErrors(refusal("radar_role_required", 409))).toEqual({
      role: "Enter the target role to run a scan.",
    });
  });

  it("names the refused fields of a 422 and nothing else", () => {
    const errors = launchErrors(refusal("validation_error", 422, { fields: ["role", "zone"] }));
    expect(errors.role).toContain("between 2 and 120");
    expect(errors.zone).toContain("between 2 and 120");
    expect(errors.general).toBeUndefined();
  });

  it("keeps any other refusal as a general message", () => {
    expect(launchErrors(refusal("engine_unavailable", 503)).general).toBe("Server message.");
  });
});

describe("failureReason", () => {
  it("explains every known code and falls back for the others", () => {
    expect(failureReason("session_cancelled")).toBe("the scan was stopped before the end.");
    expect(failureReason("llm_unavailable")).toBe(
      "no model is usable (missing key?): nothing was read.",
    );
    expect(failureReason("analysis_failed")).toBe(
      "the postings read couldn’t be analyzed (the model didn’t answer): the scan isn’t finished.",
    );
    expect(failureReason("RuntimeError")).toBe("an unexpected failure interrupted the scan.");
    expect(failureReason(null)).toBe("an unexpected failure interrupted the scan.");
  });
});
