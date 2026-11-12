import { describe, expect, it } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { programLink } from "./programLink";

describe("programLink", () => {
  it("has no link while the program is not ready", () => {
    const e = councilEvents("pr1");
    expect(programLink([e.message("m", "x")], null)).toBeNull();
  });

  it("follows the artifact of kind « program »", () => {
    const e = councilEvents("pr1");
    const events = [
      e.artifactReady("lesson", "l1", "/apprendre/lecons/l1"),
      e.artifactReady("program", "pr9", "/apprendre/programme/pr9"),
    ];
    expect(programLink(events, null)).toBe("/apprendre/programme/pr9");
  });

  it("builds the link from the artifact id when the event has no address", () => {
    const e = councilEvents("pr1");
    expect(programLink([e.artifactReady("program", "pr9", null)], null)).toBe(
      "/apprendre/programme/pr9",
    );
  });

  it.each(["https://evil.example/x", "//evil.example/x", "javascript:alert(1)"])(
    "never follows the foreign address %s",
    (url) => {
      const e = councilEvents("pr1");
      expect(programLink([e.artifactReady("program", "pr9", url)], null)).toBe(
        "/apprendre/programme/pr9",
      );
    },
  );

  it("falls back to the program known by the goal, after a reload", () => {
    expect(programLink([], "pr3")).toBe("/apprendre/programme/pr3");
  });
});
