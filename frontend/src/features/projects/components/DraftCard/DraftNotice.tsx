import { t } from "@/shared/i18n/t";
import type { DraftView } from "../viewTypes";

/**
 * L'avertissement d'un brouillon à vérifier. Les termes viennent du serveur tels quels (« 10000 »,
 * « Kubernetes »), joints par « , » : le texte n'invente ni ne reformule rien.
 */
export function DraftNotice({ draft }: { draft: DraftView }) {
  if (draft.status !== "to_check") return null;
  return (
    <p role="note" className="rounded-lg border border-amber-500/60 bg-amber-500/10 p-2 text-sm">
      {draft.flags.length > 0
        ? t("projects.draft.toCheck", { flags: draft.flags.join(", ") })
        : t("projects.draft.toCheckNoFlag")}
    </p>
  );
}
