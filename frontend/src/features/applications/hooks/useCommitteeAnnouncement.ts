import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { CommitteeView } from "../types";

type Seen = Pick<CommitteeView, "id" | "status"> | undefined;

/** What the committee re-read brings: it is deliberating, or has just ended; `null`: nothing to
 * say. */
export function describeCommitteeChange(before: Seen, after: CommitteeView): string | null {
  const sameRun = before?.id === after.id;
  if (after.status === "running") {
    return sameRun && before?.status === "running"
      ? null
      : t("applications.committeeAnnounce.running");
  }
  // What is already finished on arrival is not news: only an end seen live is announced.
  if (!sameRun || before?.status !== "running") return null;
  if (after.status === "done" && after.verdict) {
    return t("applications.committeeAnnounce.done", {
      verdict: t(`applications.committeeVote.${after.verdict}`),
    });
  }
  return t(`applications.committeeAnnounce.${after.status === "done" ? "failed" : after.status}`);
}

/**
 * The sentence to announce (live region) when the committee starts deliberating or gives its
 * verdict. A
 * run already finished on arrival announces nothing. `count` changes on each announcement, even
 * identical.
 */
export function useCommitteeAnnouncement(view: CommitteeView | undefined): {
  message: string;
  count: number;
} {
  const [last, setLast] = useState<Seen>(undefined);
  const [spoken, setSpoken] = useState({ message: "", count: 0 });
  if (view && (view.id !== last?.id || view.status !== last.status)) {
    setLast({ id: view.id, status: view.status });
    const sentence = describeCommitteeChange(last, view);
    if (sentence) setSpoken({ message: sentence, count: spoken.count + 1 });
  }
  return spoken;
}
