import { Loader2 } from "lucide-react";
import { t } from "@/shared/i18n/t";

/** Indicateur de chargement annoncé aux lecteurs d'écran (`role="status"`). */
export function LoadingState({ label }: { label?: string }) {
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 py-10 text-muted-foreground"
    >
      <Loader2 aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" />
      <span>{label ?? t("app.loading")}</span>
    </div>
  );
}
