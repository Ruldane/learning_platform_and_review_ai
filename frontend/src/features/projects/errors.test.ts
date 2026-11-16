import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/errors";
import { addFailure, openReviewSession, readableMessage, submitFailure } from "./errors";

const apiError = (code: string, status: number, details: unknown = null) =>
  new ApiError({ code, message: "Message du serveur.", status, details });

describe("submitFailure", () => {
  it("ranks each named field on its own field", () => {
    const failure = submitFailure(apiError("validation_error", 422, { fields: ["repo_url"] }));
    expect(failure.refusal).toEqual({ repoUrl: expect.stringContaining("adresse http ou https") });
    expect(failure.general).toBeNull();
  });

  it("asks for a link or a description when both are named", () => {
    const failure = submitFailure(
      apiError("validation_error", 422, { fields: ["repo_url", "description"] }),
    );
    expect(failure.refusal).toEqual({ missing: "Ajoute un lien de dépôt ou une description." });
  });

  it("names the description alone as too long", () => {
    const failure = submitFailure(apiError("validation_error", 422, { fields: ["description"] }));
    expect(failure.refusal).toEqual({
      description: "La description fait 4 000 caractères au plus.",
    });
  });

  it.each(["screenshots", "screenshots.0", "screenshots.4"])(
    "attaches %s to the screenshots",
    (field) => {
      const failure = submitFailure(apiError("validation_error", 422, { fields: [field] }));
      expect(failure.refusal?.screenshots).toMatch(/Une capture n'est pas acceptée/);
      expect(failure.general).toBeNull();
    },
  );

  it("keeps the server message for a field it does not know, never a value", () => {
    const failure = submitFailure(apiError("validation_error", 422, { fields: ["autre"] }));
    expect(failure.general).toBe("Message du serveur.");
  });

  it("writes a conflict in clear, and any other refusal with the server message", () => {
    expect(submitFailure(apiError("project_not_ready", 409)).general).toMatch(/pas encore écrit/);
    expect(submitFailure(apiError("file_too_large", 413)).general).toBe(
      "Une capture est trop volumineuse : 5 Mo au plus chacune.",
    );
    expect(submitFailure(apiError("review_unavailable", 503)).general).toBe("Message du serveur.");
    expect(submitFailure(new Error("réseau")).general).toMatch(/erreur/i);
  });
});

describe("openReviewSession", () => {
  it("reads the session of an evaluation already in progress", () => {
    expect(openReviewSession(apiError("review_in_progress", 409, { session_id: "s1" }))).toBe("s1");
  });

  it("is `null` when the server gives no session, `undefined` for any other error", () => {
    expect(openReviewSession(apiError("review_in_progress", 409, { session_id: null }))).toBeNull();
    expect(openReviewSession(apiError("project_validated", 409))).toBeUndefined();
    expect(openReviewSession(new Error("x"))).toBeUndefined();
  });
});

describe("addFailure", () => {
  it.each([
    ["profile_required", true],
    ["profile_draft_pending", true],
    ["profile_projects_full", false],
    ["entry_already_added", false],
    ["project_not_validated", false],
  ])("%s: link to the profile is %s", (code, profileLink) => {
    const failure = addFailure(apiError(code, 409));
    expect(failure.profileLink).toBe(profileLink);
    expect(failure.message).not.toBe("Message du serveur.");
  });
});

describe("readableMessage", () => {
  it("falls back to the server message for a code it has no text for", () => {
    expect(readableMessage(apiError("autre_code", 500))).toBe("Message du serveur.");
  });
});
