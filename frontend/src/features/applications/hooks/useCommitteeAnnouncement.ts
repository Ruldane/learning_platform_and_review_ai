import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { CommitteeView } from "../types";

type Seen = Pick<CommitteeView, "id" | "status"> | undefined;

/** Ce que la relecture du comité apporte : il délibère, ou il vient de se terminer ; `null` : rien à dire. */
export function describeCommitteeChange(before: Seen, after: CommitteeView): string | null {
  const sameRun = before?.id === after.id;
  if (after.status === "running") {
    return sameRun && before?.status === "running"
      ? null
      : t("applications.committeeAnnounce.running");
  }
  // Ce qui est déjà fini à l'arrivée n'est pas une nouvelle : seule une fin vue en direct s'annonce.
  if (!sameRun || before?.status !== "running") return null;
  if (after.status === "done" && after.verdict) {
    return t("applications.committeeAnnounce.done", {
      verdict: t(`applications.committeeVote.${after.verdict}`),
    });
  }
  return t(`applications.committeeAnnounce.${after.status === "done" ? "failed" : after.status}`);
}

/**
 * La phrase à annoncer (zone vocale) quand le comité se met à délibérer ou rend son verdict. Une
 * exécution déjà finie à l'arrivée n'annonce rien. `count` change à chaque annonce, même identique.
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
