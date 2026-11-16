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

/** L'icône d'un genre d'événement : décorative, le genre est écrit en texte masqué à côté. */
export function KindIcon({ kind }: { kind: ActivityKind }) {
  const Icon = ICONS[kind];
  return <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />;
}
