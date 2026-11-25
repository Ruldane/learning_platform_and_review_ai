import { AlertTriangle, BookOpen, Brain, FolderCheck, Newspaper, Radar } from "lucide-react";
import type { ActivityKind } from "../viewTypes";

const ICONS = {
  lesson: BookOpen,
  radar: Radar,
  brief: Newspaper,
  memory: Brain,
  project: FolderCheck,
  job_failed: AlertTriangle,
} as const satisfies Record<ActivityKind, typeof Radar>;

/** The icon for an event kind: decorative, the kind is written in hidden text next to it. */
export function KindIcon({ kind }: { kind: ActivityKind }) {
  const Icon = ICONS[kind];
  return <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />;
}
