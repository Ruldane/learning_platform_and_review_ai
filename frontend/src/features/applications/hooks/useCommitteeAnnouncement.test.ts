import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CommitteeView } from "../types";
import { useCommitteeAnnouncement } from "./useCommitteeAnnouncement";

const view = (over: Partial<CommitteeView> = {}): CommitteeView => ({
  id: "c1",
  cvVersionId: "v1",
  postingId: "p1",
  sessionId: "s1",
  status: "running",
  verdict: null,
  votes: [],
  objections: [],
  changes: [],
  diff: null,
  ...over,
});

describe("useCommitteeAnnouncement", () => {
  it("says nothing before there is a run, nor for a run that was already finished", () => {
    const { result, rerender } = renderHook(({ v }) => useCommitteeAnnouncement(v), {
      initialProps: { v: undefined as CommitteeView | undefined },
    });
    expect(result.current.message).toBe("");
    rerender({ v: view({ status: "done", verdict: "oui" }) });
    expect(result.current).toEqual({ message: "", count: 0 });
  });

  it("announces that the committee deliberates, then its verdict when it ends", () => {
    const { result, rerender } = renderHook(({ v }) => useCommitteeAnnouncement(v), {
      initialProps: { v: view() },
    });
    expect(result.current).toEqual({ message: "Le comité délibère.", count: 1 });
    rerender({ v: view() });
    expect(result.current.count).toBe(1);
    rerender({ v: view({ status: "done", verdict: "peut_etre" }) });
    expect(result.current).toEqual({
      message: "Le comité a rendu son verdict : Peut-être.",
      count: 2,
    });
  });

  it("announces a failure and a stop", () => {
    const failed = renderHook(({ v }) => useCommitteeAnnouncement(v), {
      initialProps: { v: view() },
    });
    failed.rerender({ v: view({ status: "failed" }) });
    expect(failed.result.current.message).toBe("Le comité s'est arrêté sans verdict.");
    const stopped = renderHook(({ v }) => useCommitteeAnnouncement(v), {
      initialProps: { v: view() },
    });
    stopped.rerender({ v: view({ status: "stopped" }) });
    expect(stopped.result.current.message).toBe("Le comité a été arrêté avant son verdict.");
  });

  it("announces a new run that starts after a finished one", () => {
    const { result, rerender } = renderHook(({ v }) => useCommitteeAnnouncement(v), {
      initialProps: { v: view({ status: "done", verdict: "oui" }) },
    });
    rerender({ v: view({ id: "c2" }) });
    expect(result.current).toEqual({ message: "Le comité délibère.", count: 1 });
  });
});
