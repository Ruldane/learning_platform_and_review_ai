import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { describeKitChange, useKitAnnouncement } from "./useKitAnnouncement";
import type { KitKindView, KitPieceView, KitView } from "../types";

const KINDS: KitKindView[] = [
  "cv",
  "letter",
  "linkedin",
  "followups",
  "form_answers",
  "company_brief",
  "pitch",
];

const piece = (kind: KitKindView, over: Partial<KitPieceView> = {}): KitPieceView => ({
  kind,
  status: "pending",
  content: "",
  flags: [],
  salaryFields: 0,
  words: null,
  sources: [],
  edited: false,
  error: null,
  updatedAt: null,
  ...over,
});

const kit = (
  running: boolean,
  done: Partial<Record<KitKindView, Partial<KitPieceView>>> = {},
): KitView => ({
  sessionId: "k1",
  running,
  pieces: KINDS.map((kind) => piece(kind, done[kind])),
});

const ready = { status: "ready", updatedAt: "2026-11-15T10:00:00Z" } as const;

describe("describeKitChange", () => {
  it("names a piece that arrives, with how it arrived", () => {
    expect(describeKitChange(kit(true), kit(true, { letter: ready }))).toBe(
      "Lettre de motivation : prête.",
    );
    expect(
      describeKitChange(kit(true), kit(true, { pitch: { ...ready, status: "to_check" } })),
    ).toBe("Pitch de présentation : à vérifier.");
    expect(describeKitChange(kit(true), kit(true, { cv: { ...ready, status: "failed" } }))).toBe(
      "CV ciblé : en échec.",
    );
  });

  it("says nothing for a piece that was already there, or when nothing changed", () => {
    const before = kit(true, { letter: ready });
    expect(describeKitChange(before, kit(true, { letter: ready }))).toBe("");
  });

  it("announces a piece rebuilt by a new run, but never one January edited", () => {
    const before = kit(true, { letter: ready, cv: { ...ready, edited: true } });
    const after = kit(true, {
      letter: { ...ready, updatedAt: "2026-11-15T11:00:00Z" },
      cv: { ...ready, edited: true, updatedAt: "2026-11-15T11:00:00Z" },
    });
    expect(describeKitChange(before, after)).toBe("Lettre de motivation : prête.");
  });

  it("closes with the count when the run ends", () => {
    const before = kit(true, { letter: ready });
    const after = kit(false, {
      letter: ready,
      pitch: { ...ready, status: "to_check" },
      cv: { ...ready, status: "failed" },
    });
    expect(describeKitChange(before, after)).toBe(
      "CV ciblé : en échec. Pitch de présentation : à vérifier. Le kit est terminé : 1 prête(s), 1 à vérifier, 1 en échec.",
    );
  });
});

describe("useKitAnnouncement", () => {
  it("stays silent on the first read, then announces what arrives", () => {
    const { result, rerender } = renderHook(({ view }) => useKitAnnouncement(view), {
      initialProps: { view: kit(true, { cv: ready }) as KitView | undefined },
    });
    expect(result.current).toBe("");
    rerender({ view: kit(true, { cv: ready, letter: ready }) });
    expect(result.current).toBe("Lettre de motivation : prête.");
  });
});
