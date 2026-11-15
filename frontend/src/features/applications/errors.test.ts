import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/errors";
import {
  applicationsErrorMessage,
  duplicateAlerts,
  existingApplicationId,
  openIntakeSessionId,
} from "./errors";
import { openedInfo } from "./navState";

const refused = (code: string, details: unknown = null) =>
  new ApiError({ code, message: `Message du serveur (${code}).`, status: 409, details });

describe("errors", () => {
  it("gives a French text to the refusals it knows, the server's message to the others", () => {
    expect(applicationsErrorMessage(refused("reminder_closed"))).toBe(
      "Cette relance est déjà traitée.",
    );
    expect(applicationsErrorMessage(refused("validation_error"))).toBe(
      "Message du serveur (validation_error).",
    );
    expect(applicationsErrorMessage(new Error("boom"))).toBe(
      "Une erreur est survenue. Réessaie dans un instant.",
    );
  });

  it("reads the near-duplicates of a 409 application_duplicate, and only those", () => {
    const alerts = [{ application_id: "a9", level: "certain", message: "Déjà là." }];
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

  it("reads the info passed to an opened fiche, ignoring anything else", () => {
    const info = [{ application_id: "a1", message: "Pour info." }];
    expect(openedInfo({ info })).toEqual(info);
    expect(openedInfo({ info: [{ message: "sans fiche" }] })).toEqual([]);
    expect(openedInfo(null)).toEqual([]);
    expect(openedInfo({ info: "x" })).toEqual([]);
  });
});
