import type { PlanDiffTask, PlanDiffView } from "@/shared/session-ui";
import type { VersionView, WeekLoadView } from "./components/viewTypes";
import type { PlanVersionOut, VersionDiffOut, WeekLoadOut } from "./types";

const SEPARATOR = " / ";

/** « {module} / {tâche} » (clé du back) : le module est ce qui précède le premier séparateur. */
function splitKey(key: string): { moduleTitle: string; title: string } {
  const at = key.indexOf(SEPARATOR);
  if (at === -1) return { moduleTitle: "", title: key };
  return { moduleTitle: key.slice(0, at), title: key.slice(at + SEPARATOR.length) };
}

/**
 * Le diff d'une version → celui du composant partagé. Le back nomme les tâches « module / tâche »
 * sans identifiant ni jour : la clé sert d'identifiant, le jour d'une tâche ajoutée n'est pas connu.
 */
export function toPlanDiffView(diff: VersionDiffOut): PlanDiffView {
  const task = (key: string): PlanDiffTask => ({ id: key, ...splitKey(key), plannedDate: null });
  return {
    added: diff.added.map(task),
    removed: diff.removed.map(task),
    moved: diff.moved.map((move) => ({
      id: move.task,
      ...splitKey(move.task),
      from: move.before,
      to: move.after,
    })),
  };
}

export function toWeekLoads(loads: WeekLoadOut[]): WeekLoadView[] {
  return loads.map((load) => ({
    rank: load.rank,
    startDate: load.start_date,
    before: load.before,
    after: load.after,
    cap: load.cap,
  }));
}

export function toVersionView(version: PlanVersionOut): VersionView {
  return {
    version: version.version,
    kind: version.kind,
    status: version.status,
    reason: version.reason,
    createdAt: version.created_at,
    review: version.review,
    diff: version.diff ? toPlanDiffView(version.diff) : null,
    weekLoads: toWeekLoads(version.week_loads),
  };
}

/** La proposition qui attend une réponse (`pending`), s'il y en a une. */
export function pendingVersion(versions: VersionView[]): VersionView | null {
  return versions.find((version) => version.status === "pending") ?? null;
}
