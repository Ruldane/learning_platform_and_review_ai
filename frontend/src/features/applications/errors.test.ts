import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/errors";
import {
  applicationsErrorMessage,
  duplicateAlerts,
  existingApplicationId,
  kitSaveErrorMessage,
  openIntakeSessionId,
  openKitSessionId,
} from "./errors";
import { openedInfo } from "./navState";

const refused = (code: string, details: unknown = null) =>
  new ApiError({ code, message: `Server message (${code}).`, status: 409, details });

describe("errors", () => {
  it("uses the interface copy for known errors and the server's message for others", () => {
    expect(applicationsErrorMessage(refused("reminder_closed"))).toBe(
      "This follow-up has already been handled.",
    );
    expect(applicationsErrorMessage(refused("validation_error"))).toBe(
      "Server message (validation_error).",
    );
    expect(applicationsErrorMessage(new Error("boom"))).toBe(
      "Something went wrong. Try again in a moment.",
    );
  });

  it("reads the near-duplicates of a 409 application_duplicate, and only those", () => {
    const alerts = [{ application_id: "a9", level: "certain", message: "Already exists." }];
    expect(duplicateAlerts(refused("application_duplicate", { alerts }))).toEqual(alerts);
    expect(duplicateAlerts(refused("application_duplicate", { alerts: [{ nope: 1 }] }))).toEqual(
      [],
    );
    expect(duplicateAlerts(refused("application_duplicate", null))).toBeNull();
    expect(duplicateAlerts(refused("application_exists", { alerts }))).toBeNull();
    expect(duplicateAlerts(new Error("x"))).toBeNull();
  });

  it("reads the existing application of a posting and the open intake session", () => {
    expect(existingApplicationId(refused("application_exists", { application_id: "a5" }))).toBe(
      "a5",
    );
    expect(
      existingApplicationId(refused("application_duplicate", { application_id: "a5" })),
    ).toBeNull();
    expect(openIntakeSessionId(refused("intake_in_progress", { session_id: "s9" }))).toBe("s9");
    expect(openIntakeSessionId(refused("intake_in_progress", {}))).toBeNull();
  });

  it("reads the kit session a 409 kit_in_progress names, and only that", () => {
    expect(openKitSessionId(refused("kit_in_progress", { session_id: "k7" }))).toBe("k7");
    expect(openKitSessionId(refused("kit_in_progress", {}))).toBeNull();
    expect(openKitSessionId(refused("posting_required", { session_id: "k7" }))).toBeNull();
  });

  it("uses the server's message when a kit edit can't be saved", () => {
    expect(applicationsErrorMessage(refused("posting_required"))).toMatch(/no linked posting/);
    expect(kitSaveErrorMessage(refused("profile_required"))).toBe(
      "Server message (profile_required).",
    );
    expect(kitSaveErrorMessage(refused("kit_item_not_found"))).toMatch(/hasn't arrived yet/);
  });

  it("reads informational matches passed to an open application", () => {
    const info = [{ application_id: "a1", message: "For reference." }];
    expect(openedInfo({ info })).toEqual(info);
    expect(openedInfo({ info: [{ message: "Missing application ID." }] })).toEqual([]);
    expect(openedInfo(null)).toEqual([]);
    expect(openedInfo({ info: "x" })).toEqual([]);
  });
});
