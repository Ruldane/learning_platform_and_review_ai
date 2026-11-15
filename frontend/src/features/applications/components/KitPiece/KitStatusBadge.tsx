import { AlertTriangle, CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { KitStatusView } from "../viewTypes";

const STATUS_ICON = {
  pending: Circle,
  ready: CheckCircle2,
  to_check: AlertTriangle,
  failed: XCircle,
} as const;

interface KitStatusBadgeProps {
  status: KitStatusView;
  /** Le kit est en cours : une pièce pas encore arrivée est « en préparation ». */
  running: boolean;
}

/** Le statut d'une pièce en toutes lettres (jamais la couleur seule), avec son icône. */
export function KitStatusBadge({ status, running }: KitStatusBadgeProps) {
  const preparing = status === "pending" && running;
  const Icon = preparing ? Loader2 : STATUS_ICON[status];
  const label = preparing
    ? t("applications.kitPiece.status.preparing")
    : t(`applications.kitPiece.status.${status}`);
  return (
    <span className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium">
      <Icon
        aria-hidden="true"
        className={`size-3.5 ${preparing ? "animate-spin motion-reduce:animate-none" : ""}`}
      />
      {label}
    </span>
  );
}
