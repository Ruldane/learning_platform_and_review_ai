import { describe, expect, it } from "vitest";
import { modificationOut, profileData, reviewOut, versionOut } from "@/test/cvApi";
import { cvErrorMessage, profileSaveError } from "./errors";
import { factLabels, fromProfileView, toProfileView } from "./profileView";
import { latestVersion, toModificationViews, toZoneViews } from "./toView";
import { ApiError } from "@/shared/api/errors";
import type { CvReviewOut, MasterProfileData, ModificationOut } from "./types";

const data = profileData() as unknown as MasterProfileData;

describe("profile view", () => {
  it("keeps the ids and the sources of the title and the summary through the form", () => {
    const sent = fromProfileView(toProfileView(data));
    expect(sent.title).toEqual({ id: "t1", text: "Ingénieure données", sources: ["cv"] });
    expect(sent.summary?.sources).toEqual(["cv", "linkedin"]);
    expect(sent.experiences?.[0]).toMatchObject({ id: "e1", sources: ["cv"] });
    expect(sent.experiences?.[0]?.achievements).toEqual([
      { id: "a1x", text: "Pipelines de 2 To par jour" },
    ]);
  });

  it("fills in the optional values so the form always has lists and nulls", () => {
    const view = toProfileView({ identity: { name: "Camille Exemple" } });
    expect(view.identity).toEqual({
      name: "Camille Exemple",
      email: null,
      phone: null,
      location: null,
      headline: null,
    });
    expect(view.experiences).toEqual([]);
    expect(view.title).toBeNull();
  });

  it("names the facts of the profile for the modification cards", () => {
    const labels = factLabels(data);
    expect(labels.get("e1")).toBe("Data engineer · Société Fictive");
    expect(labels.get("a1x")).toBe("Pipelines de 2 To par jour");
    expect(labels.get("k1")).toBe("Python");
  });
});

describe("review view", () => {
  it("cites only the facts it can still read in the profile", () => {
    const mods = [modificationOut("m1", { fact_ids: ["a1x", "gone"] })] as ModificationOut[];
    const [view] = toModificationViews(mods, factLabels(data));
    expect(view?.facts).toEqual([{ id: "a1x", label: "Pipelines de 2 To par jour" }]);
    expect(view?.author).toBe("ats_reader");
  });

  it("takes the version with the highest number as the latest", () => {
    const review = reviewOut({
      versions: [versionOut({ id: "v2", number: 2 }), versionOut({ id: "v1", number: 1 })],
    }) as unknown as CvReviewOut;
    expect(latestVersion(review)?.id).toBe("v2");
    expect(latestVersion({ ...review, versions: [] })).toBeNull();
  });

  it("ignores a layout zone it does not know", () => {
    expect(
      toZoneViews([
        { zone: "haut", original: 0.4, render: 0.3 },
        { zone: "coin", original: 1, render: 1 },
      ]),
    ).toEqual([{ zone: "haut", original: 0.4, render: 0.3 }]);
  });
});

describe("errors", () => {
  const conflict = new ApiError({ code: "profile_conflict", message: "x", status: 409 });
  const invalid = new ApiError({
    code: "validation_error",
    message: "x",
    status: 422,
    details: { fields: ["identity.name", "experiences.0.role"] },
  });

  it("uses the interface copy for known errors", () => {
    expect(cvErrorMessage(conflict)).toBe(
      "Your profile has changed: reload to see its latest version.",
    );
    expect(
      cvErrorMessage(new ApiError({ code: "profile_draft_pending", message: "x", status: 409 })),
    ).toBe(
      "A draft of your profile is waiting for approval: approve it before confirming this fact.",
    );
    expect(
      cvErrorMessage(new ApiError({ code: "other", message: "Server message.", status: 400 })),
    ).toBe("Server message.");
  });

  it("names the fields of a 422 without any value, and nothing for a 409", () => {
    expect(profileSaveError(invalid).fields).toEqual({
      "identity.name": "This field needs fixing.",
      "experiences.0.role": "This field needs fixing.",
    });
    expect(profileSaveError(conflict).fields).toEqual({});
  });
});
